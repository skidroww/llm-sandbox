from google.adk.tools import google_search
from google.adk.agents import Agent, ParallelAgent, SequentialAgent
from geopy.geocoders import Nominatim
import httpx
import pandas as pd
from mcp.server.fastmcp import FastMCP
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types
import sys


INSTRUCTIONS = """
당신은 채용 전문가 에이전트입니다.
사용자가 입력한 자기소개서를 바탕으로 아래 기준에 따라서 자기소개서를 수정할 것


##기본 평가항목
- 질문 항목에 대한 답변으로 적절한가?
- 지원자의 지원동기 등 입사에 대한 열의가 있는가?
- 핵심가치 및 인재상에 부합하는 인재인가?
- 지원 직무에 대한 역량은 갖추었는가?
- 예비 사회인으로서 다양한 경험을 하였는가?
- 팀워크, 리더십, 갈등해결 등 대인관계능력을 갖추었는가?
- 지원 기업에 대한 이해도를 갖추고자 노력하였는가?
- 다양한 변화에 대응할 인문학적 소양 등을 갖추었는가?




##가점요인
- 역량 중심으로 고민을 담아 성의껏 작성하였는가?
- 경험 위주로 근거를 갖고 구체적으로 기술하고 있는가?
- 표현능력(논리력, 문장력 등)이 우수한가?




##감점요인
- 동일 내용을 반복하고 있는가?
- 제시된 분량에 턱없이 모자라는가? (70% 이하)
- 원론적이고 추상적인 내용으로 기술하고 있는가?
- 질문과 무관한 내용이 담겨 있는가?
- 오타 및 부정확한 표현은 없는가?
- 타사 지원서를 복사하여 지원 회사명이 잘못 기재하였는가?


"""




def get_code(company_name: str) -> dict:
    """
    사용자가 회사 이름을 전달하면 해당 회사의 종목 코드를 dict형태로 반환한다.
    """
    df = pd.read_csv("C:/Users/playdata2/Downloads/myagent/skn25/data_2058_20260323.csv", encoding='cp949')
    return df[df['한글 종목명'].apply(lambda x : x.find(company_name) > -1)].to_json()


def get_company_info(company_code:str) -> dict:
    """
    종목 코드를 사용하여 회사 정보를 반환하는 코드
    회사명에서 종목코드 추출은 get_code가 담당
    company_code예시 : 005930


    """
    url = f"https://wts-info-api.tossinvest.com/api/v2/stock-infos/A{company_code}/overview"
    rt = httpx.get(url).json()
    return rt['result']['company']




company_agent = Agent(
    name='company_agent',
    model="gemini-2.5-flash",
    description='기업 정보를 사용자한테 전달하는 에이전트',
    instruction='사용자가 작성 자기소개서에서 기업에 대한 정보를 도구를 사용하여 출력하는 에이전트',
    output_key='company_info',
    tools = [get_code, get_company_info]
)




news_agent = Agent(
    name="news_agent",
    model="gemini-2.5-flash",
    instruction="사용자가 작성 자기소개서를 바탕으로 해당 기업의 주요 뉴스를 요약할 것. 앞으로 전망도 이야기할 것",
    tools=[google_search],
    output_key='news_info'
)




resume_agent = Agent(  
    name='resume_agent',
    model="gemini-2.5-flash",
    description='사용자가 작성 자기소개서를 주어진 지시에 따라 수정하여 출력하는 에이전트',
    instruction=INSTRUCTIONS,
    output_key='resume_info'
)




parallel_fet = ParallelAgent(
    name="multi_info_fetcher",
    sub_agents=[company_agent, news_agent, resume_agent],
    description="여러 정보를 동시에 요청한 내용대로 수집 및 출력"
)




summarizer = Agent(
    name='final_agent',
    model="gemini-2.5-flash",
    instruction="""
    에이전트들이 수집한 자료를 바탕으로 최종 자기 소개서를 작성하세요.
    - 기업 정보 : {company_info}
    - 기업 뉴스 : {news_info}
    - 자기소개서 수정안 : {resume_info}


    위의 정보를 바탕으로 최종 자기 소개서를 작성해서 출력하세요
    """
)


root_agent = SequentialAgent(
    name="ai_resume_system",
    sub_agents=[parallel_fet, summarizer],
    description="최종 정보를 바탕으로 자기소개서를 완성하는 에이전트"
)

mcp = FastMCP("ADK-resume")

session_service = InMemorySessionService()
runner = Runner(
    agent=root_agent,
    app_name="resume_app",
    session_service=session_service
)


@mcp.tool()
async def modify_resume(resume: str) -> str:
    """
    지원자의 자기소개서와 해당 지원하는 회사 이름과 직무를 입력하면
    에이전트 내용 수정하여 최종 수정된 자기소개서를 출력한다.
    """
    #response = root_agent.run_async(f"{resume}")
    #return str(response)
    try:
        session = await session_service.create_session(
            app_name="resume_app",
            user_id="user"
        )
        content = types.Content(role='user', parts=[types.Part(text=resume)])
        final_response = ""
        print(f"🔥 [DEBUG] 파이프라인 시작! 세션 ID: {session.id}", file=sys.stderr)
        for event in runner.run(
            session_id=session.id,
            user_id="user",
            new_message=content
        ):
            print(f"🔥 [DEBUG] 이벤트 수신: {type(event)}", file=sys.stderr)
            if event.is_final_response():
                if event.content and event.content.parts:
                    #final_response = event.content.parts[0].text
                    text_chunk = event.content.parts[0].text
                    final_response += text_chunk
                    print(f"🔥 [DEBUG] 텍스트 추가됨: {text_chunk[:50]}...", file=sys.stderr)
                else:
                    print("🔥 [DEBUG] ⚠️ is_final_response()는 통과했으나 텍스트가 비어있음", file=sys.stderr)
        
        if not final_response.strip():
            print("🔥 [DEBUG] 최종 응답이 여전히 비어있습니다. 에이전트 실행 내역을 확인해야 합니다.", file=sys.stderr)
            return "오류: 파이프라인이 실행되었으나 텍스트가 생성되지 않았습니다."
        
        return final_response
    except Exception as e:
        print("🔥 ERROR:", e, file=sys.stderr)  
        raise


if __name__=="__main__":
    print("🚀 MCP 서버 시작", file=sys.stderr)
    mcp.run()


