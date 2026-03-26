from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_classic.agents import ( AgentExecutor, create_tool_calling_agent, tool)
from langgraph.graph import StateGraph, START, END
import requests 
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from langchain_community.document_loaders import WebBaseLoader
from bs4 import SoupStrainer
import json 
from typing import TypedDict 
import asyncio 
from typing import TypedDict 
import asyncio 
from pydantic import BaseModel, Field 
from mcp.server.fastmcp import FastMCP
from bs4 import BeautifulSoup
import pandas as pd
import io 



key = ""

llm = ChatOpenAI(model='gpt-4o-mini', api_key=key)


@tool
def finance_report(company_code : str) -> str:
    """ 
    company_code : 회사 종목 코드
    종목코드 회사의 연간, 분기 재무제표를 값을 리턴하는 함수 

    return : 연간, 분기 재무제표 값 
    """
    options = Options()
    options.add_argument('--headless=new')
    options.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
    driver.get(f"https://navercomp.wisereport.co.kr/v2/company/c1010001.aspx?cmp_cd={company_code}")
    report = BeautifulSoup(driver.page_source).find_all('table', class_='gHead01 all-width')
    report_text = "\n".join([pd.read_html(io.StringIO(str(x)))[0].to_json() for x in report])
    driver.close()
    return report_text


@tool 
def get_code(company_name: str) -> dict: 
    """
    사용자가 회사 이름을 전달하면 해당 회사의 종목 코드를 dict형태로 반환한다. 
    """
    df = pd.read_csv(r"C:\Users\playdata2\OneDrive\Desktop\20260312_openapikey\stock_agent\data_2058_20260323.csv", encoding='cp949')
    return df[df['한글 종목명'].apply(lambda x : x.find(company_name) > -1)].to_json()


@tool
def get_news(company_name : str) -> str: 
    """  
    company_name : 회사명
    회사명으로 뉴스를 검색하여 해당 내용을 반환한다. 

    return : 회사명으로 검색된 뉴스의 총 텍스트값을 리턴
    """
    global total_naver_url
    client_id = "YXw4dmid0O2qTQNfhcY2"
    client_secret = "BksteLLT_U"
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret
    }
    params = {'query' : company_name , 'display' : 5, 'start': 1, "sort" : "date"}
    response = requests.get(url, headers=headers, params=params)
    #total_naver_url = [url['link'] for url in response.json()['items'] if 'naver.com' in url['link']]
    total_naver_url = [item['link'] for item in response.json()['items']]
    bs4_kwargs = {
        'parse_only' : SoupStrainer("div", id="newsct_article")
    }
    rt = WebBaseLoader(total_naver_url[0],  bs_kwargs=bs4_kwargs)

    return " ".join([WebBaseLoader(x,bs_kwargs=bs4_kwargs).load()[0].page_content.strip() for x in total_naver_url])


@tool
def get_data(company_code : str, sdate : str, edate : str) -> str:
    """
    company_code  : 종목코드 (예: 005930)
    sdate : 데이터 시작날짜 (예: 20260102)
    edate : 데이터 종료날짜 (예: 20260324)
    주식 데이터를 가져오는 함수 
    return 종목의 시가, 고가, 저가,종가, 거래량 등의 데이터 
    """
    stock_url = f"https://m.stock.naver.com/front-api/external/chart/domestic/info?symbol={company_code}&requestType=1&startTime={sdate}&endTime={edate}&timeframe=day"
    data = eval(requests.get(stock_url).text.strip())
    return json.dumps(data)



class CompanyState(TypedDict):
    question : str 
    company_finance : str 
    company_news : str 
    company_stock : str 
    final_report : str 

async def finance_node(state : CompanyState):
    """ 
    사용자 입력한 회사의 재무제표 정보를 가져와서 분석하여 리턴하는 노드
    """
    prompt = ChatPromptTemplate([
                ( "system", """당신은 금융 감독위원회의 재무 분석가입니다. 검찰 수준으로 검토할 것 
                사용자가 제공한 재무제표 데이터를 기반으로 재무 건전성, 수익성, 성장성, 안정성을 종합 분석할 것
                연간, 분기별로 별도로 분석해 
                그리고 재무 분석가의 의견으로 이야기할 것 """ ),
                ("human", "{input}"),
                ('placeholder', "{agent_scratchpad}")]
            )


    tools = [finance_report, get_code ]

    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=False, handle_parsing_errors=True)

    result = await agent_executor.ainvoke({"input" : state['question'] })
    return {'company_finance' : result['output']}

async def news_node(state : CompanyState):
    """ 
    사용자 입력한 회사의 뉴스 정보를 분석하여 리턴하는 노드
    """
    prompt_news = ChatPromptTemplate([
    ( "system", """당신은 기업 분석가입니다. 제공된 뉴스를 바탕으로 현재 기업의 상태, 미래 전망, 
     사업의 건전성등을 기업에 대한 모든 정보를 출력합니다.""" ),
     ("human", "{input}"),
     ('placeholder', "{agent_scratchpad}")]
)
    news_tools = [get_news]
    news_agent = create_tool_calling_agent(llm, news_tools, prompt_news)
    news_agent_executor = AgentExecutor(agent=news_agent, tools=news_tools, verbose=False, handle_parsing_errors=True)
    result =  await news_agent_executor.ainvoke({"input" : state['question'] })
    return {'company_news' : result['output']}

async def stock_node(state : CompanyState):
    """ 
    사용자 입력한 회사 주가정보를 분석하여 리턴하는 노드
    """
    stock_prompt = ChatPromptTemplate([
    ( "system", """당신은 20년 경력의 전업 투자가입니다. 주가의 움직임 속에 모든 정보와 투자자의 심리가 있다고 판단하고 있습니다. 주어진 데이터를 통해서 기술적 분석, 통계등을 이용해서 상태를 진단하고, 냉철하게 분석할 것 
     사용자가 종목명을 입력하면 도구를 활용해서 종목 코드를 가져오고, 도구를 활용해서 
     데이터를 가져올때 제시된 날짜부터 약 300일치 데이터를 가져올 것""" ),
     ("human", "{input}"),
     ('placeholder', "{agent_scratchpad}")]
)
    stock_tools = [get_data, get_code ]
    stock_agent = create_tool_calling_agent(llm, stock_tools, stock_prompt)
    stock_agent_executor = AgentExecutor(agent=stock_agent, tools=stock_tools, verbose=False, handle_parsing_errors=True)
    result = await stock_agent_executor.ainvoke({"input" : state['question']})
    return {'company_stock' : result['output']}

async def summarize_node(state : CompanyState):
    """에이전트 전달한 자료를 기반으로 최종 종목에서 판단하는 노드"""
    prompt = ChatPromptTemplate.from_messages([
        ('system', """ 
        에이전트들이 정리한 자료를 바탕으로 최종 종목에 대해서 매수의견을 작성하세요 
         - 기업에 대한 재무제표 정리: {company_finance}
         - 기업에 대한 뉴스정리 : {company_news}
         - 기업에 대한 주가정보 정리 : {company_stock}
        
         위의 제공된 정보를 바탕으로 최종 의견을 제시할 것
        """),
        ('human', "{question}")
    ])
    chain = prompt | llm 
    result = await chain.ainvoke( {
        'company_finance' : state.get('company_finance', ""),
        'company_news' : state.get('company_news', ""),
        'company_stock' : state.get('company_stock', ""), 
        'question' : state['question']}
    )

    return {'final_report' : result.content}

workflow = StateGraph(CompanyState)
workflow.add_node('finance_node', finance_node)
workflow.add_node('news_node', news_node)
workflow.add_node('stock_node', stock_node)
workflow.add_node('summarize_node', summarize_node)
workflow.add_edge(START, 'finance_node')
workflow.add_edge(START, 'news_node')
workflow.add_edge(START, 'stock_node')
workflow.add_edge('finance_node', 'summarize_node')
workflow.add_edge('news_node', 'summarize_node')
workflow.add_edge('stock_node', 'summarize_node')
workflow.add_edge('summarize_node', END)
app = workflow.compile()

mcp = FastMCP("stock analysis")

@mcp.tool()
async def stock_anlysis(question : str) -> str:
    """ 
    사용자가 주식 종목을 이야기하면 해당 종목에 대해서 분석해서 매수 의견을 반환하여 출력 
    :question : 2026년 3월 25일 기준으로 삼성전자 종목을 분석해봐 
    """
    try:
        result = await app.ainvoke({'question' : question})
        return result['final_report']
    except Exception as e:
        raise e  
    
if __name__=="__main__":
    mcp.run()