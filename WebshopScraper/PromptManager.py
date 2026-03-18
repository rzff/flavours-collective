import mlflow

prompt = mlflow.genai.load_prompt("prompts:/summarization-prompt/1")


if __name__ == "__main__":
    prompt = mlflow.genai.load_prompt("prompts:/summarization-prompt/2")
    print(prompt.template)
