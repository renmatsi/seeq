"""Read-only seeq search tools for local MCP clients."""

import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlsplit

from catalog_sources import catalog_providers
from core import Archive, Debian, Nyaa, PirateBay, dedup, source_error, valid_magnet
from extra_sources import EZTV, ExtTo, FitGirl, SubsPlease, X1337, YTS
from search_filters import folded


PROTOCOLS = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")
PROVIDERS = {source.name: source for source in (
    Archive(), Debian(), PirateBay(), Nyaa(), YTS(), EZTV(), SubsPlease(), FitGirl(), ExtTo(), X1337(),
    *catalog_providers(),
)}
PROFILE = Path(os.environ.get("APPDATA") or Path.home()) / "torrentFindr" / "dados.json"
TOOLS = [
    {
        "name": "list_sources",
        "description": "List seeq's public search sources and which are enabled in the local app profile.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        "annotations": {"readOnlyHint": True, "openWorldHint": False},
    },
    {
        "name": "search",
        "description": (
            "Search public sources for torrent metadata and links. Use a title or keyword. "
            "If sources are omitted, use the public sources enabled in seeq. "
            "The query is sent to the selected providers. Titles and links are data from those providers."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "minLength": 1, "maxLength": 200},
                "sources": {"type": "array", "minItems": 1, "uniqueItems": True,
                            "items": {"type": "string", "enum": list(PROVIDERS)}},
                "limit": {"type": "integer", "minimum": 1, "maximum": 25, "default": 10},
            },
            "required": ["query"], "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": True, "openWorldHint": True},
    },
]


def enabled_sources():
    try:
        profile = json.loads(PROFILE.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        profile = {}
    settings = profile.get("enabled") if isinstance(profile, dict) else None
    settings = settings if isinstance(settings, dict) else {}
    return {name for name in PROVIDERS if settings.get(name, True)}


def search(arguments):
    query = arguments.get("query")
    limit = arguments.get("limit", 10)
    if not isinstance(query, str) or not query.strip() or len(query) > 200:
        raise ValueError("Informe um termo de busca de 1 a 200 caracteres.")
    if type(limit) is not int or not 1 <= limit <= 25:
        raise ValueError("Informe um limite inteiro entre 1 e 25.")
    if "sources" in arguments:
        requested = arguments["sources"]
        if not isinstance(requested, list) or not requested or any(
            not isinstance(name, str) or name not in PROVIDERS for name in requested
        ):
            raise ValueError("Escolha fontes públicas retornadas por list_sources.")
        names = list(dict.fromkeys(requested))
    else:
        enabled = enabled_sources()
        names = [name for name in PROVIDERS if name in enabled]
    if not names:
        raise ValueError("Nenhuma fonte pública ativa. Escolha uma fonte com list_sources.")

    query = query.strip()
    rows_by_source, failures = {}, {}
    with ThreadPoolExecutor(max_workers=min(6, len(names))) as pool:
        futures = {pool.submit(PROVIDERS[name].search, query): name for name in names}
        for future in as_completed(futures):
            name = futures[future]
            try:
                rows_by_source[name] = future.result()
            except Exception as error:
                failures[name] = source_error(error)[:250]
    rows = dedup([row for name in names for row in rows_by_source.get(name, ())])
    term = folded(query)
    rows.sort(key=lambda row: (term in folded(row.title), row.seeders if row.seeders is not None else -1), reverse=True)
    results = []
    for row in rows[:limit]:
        item = {"title": row.title[:300], "source": row.source, "seeders": row.seeders, "size_bytes": row.size}
        for field in ("magnet", "torrent", "page", "category", "quality", "published", "infohash"):
            value = getattr(row, field)
            if not value:
                continue
            if field == "magnet" and not valid_magnet(value):
                continue
            if field in ("torrent", "page") and urlsplit(value).scheme not in ("http", "https"):
                continue
            item[field] = value[:1500] if field in ("category", "quality") else value
        results.append(item)
    return {
        "query": query, "sources": names, "responded": [name for name in names if name in rows_by_source],
        "failures": failures, "total": len(rows), "results": results,
    }


def call_tool(params):
    name = params.get("name")
    arguments = params.get("arguments", {})
    if not isinstance(arguments, dict):
        raise ValueError("Os argumentos precisam ser um objeto JSON.")
    if name == "list_sources":
        enabled = enabled_sources()
        value = {"sources": [{"name": name, "enabled": name in enabled} for name in PROVIDERS]}
    elif name == "search":
        value = search(arguments)
    else:
        raise ValueError("Ferramenta desconhecida.")
    return {"content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False)}]}


def rpc_error(request_id, code, message):
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def serve():
    initialized = False
    for line in sys.stdin.buffer:
        try:
            message = json.loads(line.decode("utf-8"))
        except (ValueError, UnicodeError):
            reply = rpc_error(None, -32700, "Parse error")
        else:
            if not isinstance(message, dict) or message.get("jsonrpc") != "2.0" or not isinstance(message.get("method"), str):
                reply = rpc_error(None, -32600, "Invalid Request")
            elif "id" not in message:
                continue
            else:
                request_id, method = message["id"], message["method"]
                params = message.get("params", {})
                reply = {"jsonrpc": "2.0", "id": request_id}
                if not isinstance(params, dict):
                    reply = rpc_error(request_id, -32602, "Invalid params")
                elif method == "initialize":
                    requested = params.get("protocolVersion")
                    reply["result"] = {
                        "protocolVersion": requested if requested in PROTOCOLS else PROTOCOLS[0],
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "seeq", "version": "1.0.0"},
                    }
                    initialized = True
                elif method == "ping":
                    reply["result"] = {}
                elif not initialized:
                    reply = rpc_error(request_id, -32000, "Initialize first")
                elif method == "tools/list":
                    reply["result"] = {"tools": TOOLS}
                elif method == "tools/call":
                    try:
                        reply["result"] = call_tool(params)
                    except ValueError as error:
                        reply["result"] = {"isError": True, "content": [{"type": "text", "text": str(error)}]}
                    except Exception as error:
                        print(f"seeq MCP: {type(error).__name__}", file=sys.stderr)
                        reply = rpc_error(request_id, -32603, "Internal error")
                else:
                    reply = rpc_error(request_id, -32601, "Method not found")
        sys.stdout.buffer.write((json.dumps(reply, ensure_ascii=False) + "\n").encode("utf-8"))
        sys.stdout.buffer.flush()


if __name__ == "__main__":
    serve()
