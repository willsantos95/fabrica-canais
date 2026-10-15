"""Converte os JSON gerados por build_workflows.py em código do Workflow SDK do n8n
(para criar os fluxos pelo conector MCP com as credenciais já existentes)."""
import json, re, sys, uuid

CREDS = {
    "Fabrica DB": ("postgres", "CgrwOpkbdW4VgyTc", "Postgres - Fabrica"),
    "Fabrica Worker": ("httpHeaderAuth", "R96vQrkAjGn3GHEt", "Auth - Fabrica Worker"),
    "Fabrica Callback": ("httpHeaderAuth", "dBAcX42kLwL5n3eW", "Auth - Fabrica Callback"),
    "OpenAI API": ("httpHeaderAuth", "9OK91AZnXE70dKic", "OpenAi - Fabrica"),
    "Evolution API": ("evolutionApi", "570ZlMjp90Xd9ZZk", "Evolution API"),
}
SETTINGS = ("retryOnFail", "maxTries", "waitBetweenTries", "alwaysOutputData", "onError", "disabled", "executeOnce")

def js(v, ind=0):
    pad = "  " * ind
    if isinstance(v, str):
        if v.startswith("="):
            return "expr(" + json.dumps(v[1:], ensure_ascii=False) + ")"
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, dict):
        if not v:
            return "{}"
        items = [f"{pad}  {json.dumps(k, ensure_ascii=False)}: {js(x, ind + 1)}" for k, x in v.items()]
        return "{\n" + ",\n".join(items) + f"\n{pad}}}"
    if isinstance(v, list):
        if not v:
            return "[]"
        return "[\n" + ",\n".join(f"{pad}  {js(x, ind + 1)}" for x in v) + f"\n{pad}]"
    return json.dumps(v)

def evolution_params(p):
    """HTTP para a Evolution → nó oficial da comunidade (credencial evolutionApi)."""
    body = p["jsonBody"]
    m = re.search(r"number: (.+?), text: (.+?) \}\) \}\}", body)
    return {
        "resource": "messages-api",
        "operation": "send-text",
        "instanceName": "={{ $('Config').first().json.evolution_instance }}",
        "remoteJid": "={{ " + m.group(1) + " }}",
        "messageText": "={{ " + m.group(2) + " }}",
    }

def convert(path, wf_id, wf_name):
    d = json.load(open(path))
    names = {}
    out = ["import { workflow, node, trigger, expr } from '@n8n/workflow-sdk';", ""]
    triggers = []
    for i, n in enumerate(d["nodes"]):
        var = f"n{i}"
        names[n["name"]] = var
        typ, ver, params = n["type"], n["typeVersion"], dict(n["parameters"])
        creds = n.get("credentials") or {}
        cred_js = {}
        if n["name"].startswith("WhatsApp"):
            typ, ver, params = "n8n-nodes-evolution-api.evolutionApi", 1, evolution_params(params)
            creds = {"evolutionApi": {"name": "Evolution API"}}
        for _, c in creds.items():
            key, cid, cname = CREDS[c["name"]]
            cred_js[key] = {"id": cid, "name": cname}
        cfg = {"name": n["name"], "parameters": params}
        if cred_js:
            cfg["credentials"] = cred_js
        for s in SETTINGS:
            if s in n:
                cfg[s] = n[s]
        if "webhookId" in n:
            cfg["webhookId"] = str(uuid.uuid4())  # novo id: não colide com os fluxos antigos
        cfg["position"] = n["position"]
        is_trig = typ.endswith(("Trigger", "trigger")) or typ.endswith("errorTrigger")
        fn = "trigger" if is_trig else "node"
        if is_trig:
            triggers.append(n["name"])
        out.append(f"const {var} = {fn}({{\n  type: {json.dumps(typ)},\n  version: {ver},\n  config: {js(cfg, 1)},\n  output: [{{}}]\n}});\n")
    conns = d["connections"]
    chain = []
    for t in triggers:
        cur, seq = t, [names[t]]
        while cur in conns:
            nxt = conns[cur]["main"][0][0]["node"]
            seq.append(names[nxt])
            cur = nxt
            if len(chain) and names[nxt] in chain[0]:
                break
        chain.append(seq)
    wf = f"export default workflow({json.dumps(wf_id)}, {json.dumps(wf_name)})"
    for i, seq in enumerate(chain):
        if i == 0:
            wf += f"\n  .add({seq[0]})" + "".join(f"\n  .to({v})" for v in seq[1:])
        else:  # segundo gatilho entra no mesmo nó seguinte (fan-in)
            wf += f"\n  .add({seq[0]})\n  .to({seq[1]})"
    out.append(wf + ";\n")
    return "\n".join(out)

if __name__ == "__main__":
    src, wid, name, dst = sys.argv[1:5]
    open(dst, "w").write(convert(src, wid, name))
