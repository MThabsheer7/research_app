"""
Shared LLM Provider for all agent nodes.
Allows dynamic switching between Google variants, Local, and OpenAI-compatible endpoints.
"""
import os
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
