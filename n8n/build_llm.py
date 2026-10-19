"""Gera n8n/sdk/factory.llm.js: um único ponto para chamar IA de texto na fábrica.

Entrada (Execute Workflow): body (pedido no formato da OpenAI Responses), order (ex.: ["prepared","gemini","openai"]),
prepared (texto pronto, ex.: roteiro escrito pelo Claude), gemini ({model, search_model}), stage (nome da etapa).
Saída: { done, response } com response no formato da OpenAI (output_text, usage, model) + provider.
Tenta os provedores na ordem; se um falhar (cota, erro, resposta cortada), passa para o próximo.
"""
from pathlib import Path
from build_fase2 import OUT, WF

HERE = Path(__file__).parent
code = lambda name: (HERE / "llm" / name).read_text("utf-8")
OPENAI = {"httpHeaderAuth": {"id": "9OK91AZnXE70dKic", "name": "OpenAi - Fabrica"}}
GEMINI = {"googlePalmApi": {"id": "MnXJZD0zO0Nx6MpZ", "name": "Google Gemini(PaLM) Api account"}}


def build_llm() -> str:
    wf = WF("factory-llm", "factory.llm")
    wf.node("t_sub", "n8n-nodes-base.executeWorkflowTrigger", 1.2, "Pedido de IA", {
        "inputSource": "workflowInputs", "workflowInputs": {"values": [
            {"name": "body", "type": "object"}, {"name": "order", "type": "array"},
            {"name": "prepared", "type": "string"}, {"name": "gemini", "type": "object"}, {"name": "stage", "type": "string"}]}},
        [0, 0], fn="trigger", output=[{"body": {}, "order": ["gemini", "openai"], "prepared": "", "gemini": {}, "stage": "script"}])
    wf.node("plano", "n8n-nodes-base.code", 2, "Plano", {"jsCode": """const i = $input.first().json;
const valid = ['prepared', 'gemini', 'openai'];
const order = (Array.isArray(i.order) && i.order.length ? i.order : ['openai']).filter(p => valid.includes(p));
return [{ json: { body: i.body || {}, order, prepared: i.prepared || '', gemini: i.gemini || {}, stage: i.stage || '', step: 0, errors: [] } }];
"""}, [240, 0], output=[{"body": {}, "order": [], "step": 0, "errors": []}])
    wf.node("prox", "n8n-nodes-base.code", 2, "Próximo provedor", {"jsCode": code("proximo.js")}, [480, 0],
            output=[{"provider": "gemini", "model": "gemini-2.5-flash", "request": {}, "step": 0, "errors": []}])
    wf.node("rota", "n8n-nodes-base.switch", 3.4, "Provedor", {
        "mode": "expression", "numberOutputs": 3,
        "output": "={{ ({ prepared: 0, openai: 1, gemini: 2 })[$json.provider] }}"}, [720, 0], fn="switchCase")
    wf.node("pronto", "n8n-nodes-base.noOp", 1, "Texto pronto", {}, [960, -200], output=[{}])
    wf.node("openai", "n8n-nodes-base.httpRequest", 4.2, "OpenAI", {
        "method": "POST", "url": "https://api.openai.com/v1/responses",
        "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth",
        "sendBody": True, "specifyBody": "json", "jsonBody": "={{ JSON.stringify($json.request) }}",
        "options": {"timeout": 900000}}, [960, 0], OPENAI, onError="continueRegularOutput", alwaysOutputData=True,
        output=[{"output_text": "x"}])
    wf.node("gemini", "n8n-nodes-base.httpRequest", 4.2, "Gemini", {
        "method": "POST", "url": "={{ 'https://generativelanguage.googleapis.com/v1beta/models/' + $json.model + ':generateContent' }}",
        "authentication": "predefinedCredentialType", "nodeCredentialType": "googlePalmApi",
        "sendBody": True, "specifyBody": "json", "jsonBody": "={{ JSON.stringify($json.request) }}",
        "options": {"timeout": 900000}}, [960, 200], GEMINI, onError="continueRegularOutput", alwaysOutputData=True,
        output=[{"candidates": []}])
    wf.node("aval", "n8n-nodes-base.code", 2, "Avaliar resposta", {"jsCode": code("avaliar.js")}, [1200, 0],
            output=[{"done": True, "response": {}}])
    wf.node("fim", "n8n-nodes-base.if", 2.2, "Respondeu?", {"conditions": {
        "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose"},
        "conditions": [{"leftValue": "={{ $json.done }}", "rightValue": True,
                        "operator": {"type": "boolean", "operation": "true", "singleValue": True}}],
        "combinator": "and"}, "options": {}}, [1440, 0], fn="ifElse")
    wf.node("resp", "n8n-nodes-base.code", 2, "Resposta", {"jsCode": "return [{ json: $input.first().json.response }];"},
            [1680, -100], output=[{"output_text": "x", "provider": "gemini"}])
    return wf.render(
        "  .add(t_sub)\n  .to(plano)\n  .to(prox)\n  .to(rota\n    .onCase(0, pronto.to(aval))\n    .onCase(1, openai.to(aval))\n"
        "    .onCase(2, gemini.to(aval)))\n  .add(aval)\n  .to(fim.onTrue(resp).onFalse(prox))")


if __name__ == "__main__":
    (OUT / "factory.llm.js").write_text(build_llm(), "utf-8")
    print("ok")
