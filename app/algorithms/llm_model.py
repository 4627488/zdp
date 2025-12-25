from typing import Optional
import numpy as np
import os
import json
from dotenv import load_dotenv
from openai import OpenAI

from .base import ReliabilityModel

load_dotenv()


class LLMModel(ReliabilityModel):
    """LLM-Assisted (DeepSeek) model for reliability prediction."""

    name: str
    api_key: Optional[str]
    client: Optional[OpenAI]
    train_data: Optional[np.ndarray]

    def __init__(self) -> None:
        self.name: str = "LLM-Assisted (DeepSeek)"
        self.api_key: Optional[str] = os.getenv("DEEPSEEK_API_KEY")
        self.client: Optional[OpenAI] = None
        if self.api_key:
            try:
                self.client = OpenAI(api_key=self.api_key, base_url="https://api.deepseek.com")
            except Exception as e:
                print(f"Failed to initialize OpenAI client: {e}")
        self.train_data: Optional[np.ndarray] = None

    def fit(self, tbf_train: np.ndarray) -> None:
        """Fit the LLM model by storing training data.

        Args:
            tbf_train: Array of training time between failures.
        """
        self.train_data = tbf_train

    def predict(self, n_steps: int, last_cumulative_time: float) -> np.ndarray:
        """Predict cumulative failure times using LLM.

        Args:
            n_steps: Number of steps to predict.
            last_cumulative_time: The last cumulative failure time.

        Returns:
            Array of predicted cumulative times.
        """
        if not self.client or self.train_data is None:
            return self._mock_predict(n_steps, last_cumulative_time)

        try:
            # Use the last 50 data points to provide context without exceeding limits
            recent_tbf: list[float] = (
                self.train_data[-50:].tolist()
                if len(self.train_data) > 50
                else self.train_data.tolist()
            )
            
            prompt: str = f"""
            You are a software reliability engineering expert.
            I have a sequence of Time Between Failures (TBF) for a software system: {recent_tbf}.
            The last cumulative failure time was {last_cumulative_time}.
            
            Please predict the cumulative failure times for the next {n_steps} failures.
            Analyze the trend in the TBF data (e.g., reliability growth if TBF is increasing, or decay if decreasing).
            
            Return ONLY a JSON list of {n_steps} numbers representing the predicted cumulative times.
            Do not include any markdown formatting, code blocks, or explanation.
            The output should be a raw JSON list, e.g.: [100.5, 110.2, 125.0]
            """

            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that outputs only raw JSON."},
                    {"role": "user", "content": prompt}
                ],
                stream=False,
                temperature=0.5
            )

            content: str = response.choices[0].message.content.strip()
            
            # Clean up potential markdown code blocks if the model ignores instructions
            if content.startswith("```"):
                content = content.split("\n", 1)[1]
                if content.endswith("```"):
                    content = content.rsplit("\n", 1)[0]
            
            predictions: list[float] = json.loads(content)
            
            if not isinstance(predictions, list) or len(predictions) != n_steps:
                print(f"Invalid prediction format from LLM: {content}")
                return self._mock_predict(n_steps, last_cumulative_time)
                
            return np.array(predictions)

        except Exception as e:
            print(f"Error calling DeepSeek API: {e}")
            return self._mock_predict(n_steps, last_cumulative_time)

    def _mock_predict(self, n_steps: int, last_cumulative_time: float) -> np.ndarray:
        """Mock prediction as fallback when LLM is unavailable.

        Args:
            n_steps: Number of steps to predict.
            last_cumulative_time: The last cumulative failure time.

        Returns:
            Array of mock predicted cumulative times.
        """
        predictions: list[float] = []
        current_time: float = last_cumulative_time
        
        # Simulate increasing TBF (reliability growth)
        base_tbf: float = 10.0 
        if self.train_data is not None and len(self.train_data) > 0:
            base_tbf = (
                np.mean(self.train_data[-5:])
                if len(self.train_data) >= 5
                else np.mean(self.train_data)
            )
        
        for i in range(n_steps):
            # Growth factor
            growth: float = 1.0 + (i * 0.05)
            current_time += base_tbf * growth
            predictions.append(current_time)
            
        return np.array(predictions)
