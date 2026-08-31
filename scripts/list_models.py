from openai import OpenAI
import config

def list_models():
    client = OpenAI(
        base_url=config.LLM_BASE_URL,
        api_key=config.LLM_API_KEY
    )
    try:
        models = client.models.list()
        print("--- 可用模型列表 ---")
        for m in models:
            print(m.id)
    except Exception as e:
        print(f"列出模型失败: {e}")

if __name__ == "__main__":
    list_models()
