"""
Shared LLM Provider for all agent nodes.
Allows dynamic switching between Google variants, Local, and OpenAI-compatible endpoints.
"""
import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class LLMProvider:
    def __init__(self):
        self.provider = os.environ.get("LLM_PROVIDER", "google").lower()
        self.base_url = os.environ.get("LLM_BASE_URL")
        self.api_key = os.environ.get("LLM_API_KEY")
        self.model = os.environ.get("LLM_MODEL", "gemini-2.5-flash")
        
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
        )

    def _format_messages(self, messages):
        """
        Adapts the roles based on the model.
        For example, Gemma models on Google AI Studio reject the 'system' role.
        """
        needs_system_to_user = "gemma" in self.model.lower() or os.environ.get("NO_SYSTEM_ROLE", "false").lower() == "true"
        
        if not needs_system_to_user:
            return messages

        formatted = []
        system_acc = ""
        for m in messages:
            if m["role"] == "system":
                system_acc += m["content"] + "\n\n"
            elif m["role"] == "user":
                content = system_acc + m["content"] if system_acc else m["content"]
                formatted.append({"role": "user", "content": content})
                system_acc = "" # reset
            else:
                formatted.append(m)
        return formatted

    def generate_structured(self, messages, response_format, max_tokens=1024):
        """Generates structured output parsing into the provided Pydantic model."""
        msgs = self._format_messages(messages)
        
        # Google's Gemma models do not support the native parse endpoint or JSON mode
        use_manual_json = "gemma" in self.model.lower() or os.environ.get("MANUAL_JSON_PARSING", "false").lower() == "true"

        if use_manual_json:
            # Append schema to the last message
            schema = response_format.model_json_schema()
            prompt_injection = (
                "\n\nIMPORTANT: You MUST respond ONLY with a raw JSON object structured exactly "
                "like the following schema. Populate all keys with the actual generated data "
                "based on your analysis. DO NOT just return the schema definitions.\n"
                f"{json.dumps(schema)}"
            )
            msgs[-1]["content"] += prompt_injection
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=msgs,
                max_tokens=max_tokens
            )
            
            content = response.choices[0].message.content
            
            # Clean up markdown formatting if the model outputs ```json ... ```
            content = content.replace("```json", "").replace("```", "").strip()
            
            return response_format.model_validate_json(content)
            
        else:
            # Models that natively support structured outputs (GPT-4o, Gemini 1.5, Qwen via vLLM)
            response = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=msgs,
                response_format=response_format,
                max_tokens=max_tokens
            )
            return response.choices[0].message.parsed

    def generate_text(self, messages, max_tokens=1024):
        """Generates raw text format output."""
        msgs = self._format_messages(messages)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=msgs,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content

# Singleton instance for the agent nodes
llm = LLMProvider()
