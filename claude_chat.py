#!/usr/bin/env python3
"""
Claude 터미널 채봇
"""

import os
from anthropic import Anthropic

def main():
    # API 키 확인
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ API 키가 설정되지 않았습니다.")
        print("설정 방법:")
        print('  export ANTHROPIC_API_KEY="your-api-key-here"')
        return
    
    # Claude 클라이언트 초기화
    client = Anthropic()
    
    # 대화 히스토리
    conversation_history = []
    
    print("=" * 60)
    print("🤖 Claude 터미널 채봇")
    print("=" * 60)
    print("'quit' 또는 'exit'를 입력하여 종료합니다.")
    print("=" * 60)
    print()
    
    while True:
        # 사용자 입력
        try:
            user_input = input("👤 당신: ").strip()
        except KeyboardInterrupt:
            print("\n\n👋 프로그램을 종료합니다.")
            break
        
        # 종료 조건
        if user_input.lower() in ["quit", "exit", "종료"]:
            print("\n👋 프로그램을 종료합니다.")
            break
        
        # 빈 입력 무시
        if not user_input:
            continue
        
        # 메시지 히스토리에 추가
        conversation_history.append({
            "role": "user",
            "content": user_input
        })
        
        # Claude API 호출
        try:
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                system="당신은 한국어를 능숙하게 사용하는 친절한 AI 어시스턴트입니다. 사용자의 질문에 간단하고 명확하게 답변해주세요.",
                messages=conversation_history
            )
            
            # 응답 메시지
            assistant_message = response.content[0].text
            
            # 히스토리에 추가
            conversation_history.append({
                "role": "assistant",
                "content": assistant_message
            })
            
            # 출력
            print(f"\n🤖 Claude: {assistant_message}\n")
            
        except Exception as e:
            print(f"\n❌ 오류 발생: {e}\n")
            # 마지막 사용자 메시지 제거 (재시도 위함)
            conversation_history.pop()

if __name__ == "__main__":
    main()
