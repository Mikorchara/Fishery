import config
from core.llm_advisor import FisheryAdvisor

def test_llm():
    print("--- 正在测试 NVIDIA MiniMax API 连接 ---")
    advisor = FisheryAdvisor()
    
    # 模拟一些传感器数据
    mock_data = {
        "temp": "26.5",
        "ph": "7.2",
        "oxygen": "5.8"
    }
    
    print(f"输入数据: {mock_data}")
    result = advisor.get_advice(mock_data)
    
    print("\n--- AI 诊断结果 ---")
    print(result)
    print("-----------------------------------")

if __name__ == "__main__":
    try:
        # 强制设置输出编码为 utf-8，避免 Windows 命令行乱码
        import sys
        import io
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
            
        test_llm()
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
