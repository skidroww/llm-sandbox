from crewai import Agent, Task, Crew, Process, LLM


from dotenv import load_dotenv
load_dotenv()
import os
os.environ["OPENAI_API_KEY"] = ""




llm = LLM(
    model='gpt-4.1-2025-04-14',
    temperature=0.4
)


Casanova_agent = Agent(
    role="연애 전문가",
    goal="이성이 좋아할 만한 매력적인 글을 작성한다.",
    backstory="""
    당신은 연애 편지를 잘 쓰는 작가입니다.
    다른 사람이 초안을 작성한 내용을 당신의 탁월한 감각으로 편집합니다.
    """,
    verbose=True,
    allow_delegation=False,
    llm=llm
)


Writer_agent = Agent(
    role='편지 작성자',
    goal="이성이 좋아할 만한 편지의 초안을 작성한다.",
    backstory="""
    이성에게 편지를 자주 작성하며, 상대방의 취향을 잘 파악하는 사람입니다.
    """,
    verbose=True,
    allow_delegation=False,
    llm=llm
)


write_task = Task(
    description="""
    상대방이 좋아하는 것들 : 샤넬, 플스5, 맥북
    MBTI : ISTP
    위 정보를 바탕으로 편지의 초안을 작성할 것.
    """,
    expected_output="상대방의 취향과 성향을 반영한 편지 초안.",
    agent=Writer_agent
)


modify_task = Task(
    description="""
    제시된 편지 초안을 카사노바 입장에서 더욱 매력적으로 수정할 것.
    """,
    # 사용자의 이모지 사용 금지 규칙을 반영하여 관련 지시어 제거
    expected_output="달콤하고 매력적인 말투의 편지 내용 (약 300~500 단어).",
    agent=Casanova_agent
)


crew = Crew(
    # 논리적 흐름에 따라 초안 작성자(Writer)를 먼저 배치하는 것이 일반적이나,
    # Task의 순서가 Process.sequential에 의해 결정되므로 agents 배열의 순서는 실행에 영향을 주지 않습니다.
    agents=[Writer_agent, Casanova_agent],
    tasks=[write_task, modify_task],
    process=Process.sequential,
    verbose=True
)


result = crew.kickoff()


# ===========================================
# 5. 결과 출력
# ===========================================
print("\n\n=== 최종 결과 ===\n")
# 최신 버전의 CrewOutput 객체에서 원시 텍스트(raw text)를 추출하여 출력합니다.
print(result.raw)
