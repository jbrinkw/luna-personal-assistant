# This script generates a model object based on the specified intelligence level and resource usage.
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ModelRouter:
    def __init__(self, intelligence_level='medium', use_local_resources=False):
        self.intelligence_level = intelligence_level
        self.use_local_resources = use_local_resources
        self.model = self.load_model()

    def load_model(self):
        # Load the appropriate model based on the intelligence level and resource usage
        if self.use_local_resources:
            return self.load_local_model()
        else:
            if self.intelligence_level == 'low':
                return self.load_low_intelligence_model()
            elif self.intelligence_level == 'high':
                return self.load_high_intelligence_model()
            else:
                return self.load_medium_intelligence_model()

    def load_local_model(self):
        # Logic to load local model (placeholder for now)
        # This would be implemented later
        return None

    def load_low_intelligence_model(self):
        # Low intelligence API model (gpt-4o-mini)
        return ChatOpenAI(model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))

    def load_medium_intelligence_model(self):
        # Medium intelligence API model (gpt-4o)
        return ChatOpenAI(model="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))

    def load_high_intelligence_model(self):
        # High intelligence API model (o3-mini)
        return ChatOpenAI(model="o3-mini", api_key=os.getenv("OPENAI_API_KEY"))

    def get_model(self):
        return self.model

    def set_intelligence_level(self, level):
        self.intelligence_level = level
        self.model = self.load_model()

    def set_use_local_resources(self, use_local):
        self.use_local_resources = use_local
        self.model = self.load_model()
