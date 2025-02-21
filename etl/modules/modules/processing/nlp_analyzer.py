import json
import instructor
from groq import Groq
from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    tool_name: str = Field(description="The name of the tool to call")
    tool_parameters: str = Field(description="JSON string of tool parameters")


class ResponseModel(BaseModel):
    tool_calls: list[ToolCall]


class ArabicNLPAnalyzer:
    def __init__(self, api_key, model, temperature, maxtokens, logger) -> None:
        self.model = model
        self.temperature = temperature
        self.maxtokens = maxtokens
        self.logger = logger

        self.client = instructor.from_groq(
            Groq(api_key=api_key), 
            mode=instructor.Mode.JSON
            )
        self.general_topics = [
                "السياسة والحكم",
                "الاقتصاد والأعمال",
                "التكنولوجيا والابتكار",
                "العلوم والبيئة",
                "الصحة والطب",
                "الثقافة والمجتمع",
                "الرياضة",
                "أنماط الحياة والرفاهية"
            ]
        self.tool_schema = {
            "name": "get_arabic_nlp_analysis",
            "description": f"Get and combine arabic NLP analysis",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": f"The arabic topic related to the text in {self.general_topics}"
                    },
                    "geolocations": {
                        "type": "list",
                        "description": "The list of arabic geolocations mentioned in the text"
                    },
                    "entities": {
                        "type": "list",
                        "description": f"The arabic recognized entities from the text"
                    }
                },
                "required": ["geolocations", "topic", "entities"]
            }
        }

    def run_conversation(self, user_prompt):
        # Prepare the messages
        messages = [
            {
                "role": "system",
                "content": f"You are a arabic nlp tasks assistant that can use tools. You have access to the following tool: {self.tool_schema}"
            },
            {
                "role": "user",
                "content": user_prompt,
            }
        ]

        response = self.client.chat.completions.create(
            model=self.model,
            response_model=ResponseModel,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.maxtokens,
        )

        for call in response.tool_calls:
            if call.tool_name == "get_arabic_nlp_analysis":
                return json.loads(call.tool_parameters) 
        
        return None
