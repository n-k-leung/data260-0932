import ollama

class ModelClient:
    def __init__(self, model="qwen3:8b",base_url="http://localhost:11434"):
        self.model = model
        self.client=ollama.Client(host=base_url)
    def complete(self,messages,tools=None,options=None):
        response=self.client.chat(model=self.model, messages=messages,tools=tools,options=options)
        input_tokens=response.get("prompt_eval_count",0)
        output_tokens=response.get("eval_count",0)
        tool_calls = []
        for call in response["message"].get("tool_calls") or []:
            tool_calls.append({
                "name": call["function"]["name"],
                "arguments": dict(call["function"]["arguments"]),
            })
        return{
            "content":response["message"]["content"],
            "input_tokens":input_tokens,
            "output_tokens":output_tokens,
            "total_tokens":input_tokens+output_tokens,
            "tool_calls":tool_calls,
        }