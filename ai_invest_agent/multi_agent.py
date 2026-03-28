from __future__ import annotations

import json
import os
from dataclasses import asdict
from typing import Any

import requests

from ai_invest_agent.models import (
    AnalysisPlanItem,
    InvestmentRequest,
    InvestorPersona,
    MultiAgentAnalysis,
    Recommendation,
    ResearchFinding,
    SecuritySnapshot,
    StockInsight,
    TopicSelection,
    VerificationResult,
)


OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
DEFAULT_MODEL = "gpt-4.1-mini"


def run_multi_agent_analysis(
    request: InvestmentRequest,
    recommendations: list[Recommendation],
    snapshots: list[SecuritySnapshot],
) -> MultiAgentAnalysis:
    return _run_multi_agent_analysis(request, recommendations, snapshots)


def build_rule_based_multi_agent_analysis(
    request: InvestmentRequest,
    recommendations: list[Recommendation],
    snapshots: list[SecuritySnapshot],
) -> MultiAgentAnalysis:
    original_api_key = os.environ.pop("OPENAI_API_KEY", None)
    try:
        return _run_multi_agent_analysis(request, recommendations, snapshots)
    finally:
        if original_api_key is not None:
            os.environ["OPENAI_API_KEY"] = original_api_key


def _run_multi_agent_analysis(
    request: InvestmentRequest,
    recommendations: list[Recommendation],
    snapshots: list[SecuritySnapshot],
) -> MultiAgentAnalysis:
    snapshot_map = {item.symbol: item for item in snapshots}
    selected = [item for item in recommendations if item.symbol in snapshot_map][:5]

    persona = _build_persona_agent(request)
    topics = _build_topic_agent(request, persona, selected, snapshot_map)
    plan = _build_planning_agent(topics, snapshot_map)
    research = _build_research_agent(request, plan, snapshot_map)
    insights = _build_insight_agent(request, persona, selected, research, snapshot_map)
    markdown_report = _build_writing_agent(request, persona, selected, insights, snapshot_map)
    verification = _build_verification_agent(request, selected, snapshots, markdown_report)

    return MultiAgentAnalysis(
        persona=persona,
        topics=topics,
        plan=plan,
        research=research,
        insights=insights,
        markdown_report=markdown_report,
        verification=verification,
        model_map=_agent_model_map(),
    )


def _build_persona_agent(request: InvestmentRequest) -> InvestorPersona:
    prompt = (
        "너는 전문 투자 심리 분석가야. 사용자가 제공한 자산 규모({asset_krw}), "
        "투자 성향({propensity}), 희망 시장({market}), 및 투자 기간({duration}) 데이터를 분석해줘. "
        "이 사용자가 어떤 위험 감수 능력을 갖췄는지, 어떤 섹터에 흥미를 느낄지, 그리고 투자 결정 시 "
        "가장 중요하게 여길 가치가 무엇인지 '투자자 페르소나' 보고서를 작성해줘. "
        "이 결과는 다음 단계인 주제 추천 에이전트에게 전달될 거야."
    ).format(
        asset_krw=request.asset_krw,
        propensity=request.propensity,
        market=request.market,
        duration=request.duration,
    )
    fallback = _rule_based_persona(request)
    payload = {
        "summary": fallback.summary,
        "risk_tolerance": fallback.risk_tolerance,
        "sector_interests": fallback.sector_interests,
        "decision_values": fallback.decision_values,
    }
    response = _call_json_agent("persona", prompt, payload)
    return InvestorPersona(
        summary=_coerce_str(response, "summary", fallback.summary),
        risk_tolerance=_coerce_str(response, "risk_tolerance", fallback.risk_tolerance),
        sector_interests=_coerce_list(response, "sector_interests", fallback.sector_interests),
        decision_values=_coerce_list(response, "decision_values", fallback.decision_values),
        source="llm" if response else fallback.source,
    )


def _build_topic_agent(
    request: InvestmentRequest,
    persona: InvestorPersona,
    recommendations: list[Recommendation],
    snapshot_map: dict[str, SecuritySnapshot],
) -> list[TopicSelection]:
    fallback_items = []
    stock_payloads = []
    for item in recommendations:
        snapshot = snapshot_map[item.symbol]
        fallback_items.append(
            TopicSelection(
                symbol=item.symbol,
                name=item.name,
                rationale=(
                    f"{persona.risk_tolerance} 성향과 {request.duration} 관점에서 "
                    f"{item.rationale}. RSI {_fmt_num(snapshot.technicals.rsi)}, "
                    f"MACD {_fmt_num(snapshot.technicals.macd)}, ROE {_fmt_num(snapshot.fundamentals.roe)}, "
                    f"PER {_fmt_num(snapshot.fundamentals.per)}."
                ),
            )
        )
        stock_payloads.append(
            {
                "symbol": item.symbol,
                "name": item.name,
                "rationale": item.rationale,
                "rsi": snapshot.technicals.rsi,
                "macd": snapshot.technicals.macd,
                "roe": snapshot.fundamentals.roe,
                "per": snapshot.fundamentals.per,
                "risk_level": item.risk_level,
            }
        )

    prompt = (
        "너는 주식 시장 전략가야. 앞서 분석된 '투자자 페르소나'와 현재 {market} 시장의 종목 리스트를 검토해줘. "
        "사용자의 성향에 가장 적합한 5가지 핵심 종목을 선정하고, 왜 이 종목들이 현재 이 사용자에게 최적인지 "
        "간단한 추천 사유를 요약해줘. 기술적 지표(RSI, MACD)와 기본적 지표(ROE, PER)를 모두 고려해야 해.\n\n"
        "투자자 페르소나:\n{persona}\n\n종목 데이터:\n{stocks}"
    ).format(
        market=request.market,
        persona=json.dumps(asdict(persona), ensure_ascii=False),
        stocks=json.dumps(stock_payloads, ensure_ascii=False),
    )
    response = _call_json_agent("topic_selection", prompt, {"topics": [asdict(item) for item in fallback_items]})
    topics = response.get("topics") if response else None
    if not isinstance(topics, list):
        return fallback_items

    resolved: list[TopicSelection] = []
    for raw, fallback in zip(topics[: len(fallback_items)], fallback_items):
        resolved.append(
            TopicSelection(
                symbol=_coerce_str(raw, "symbol", fallback.symbol),
                name=_coerce_str(raw, "name", fallback.name),
                rationale=_coerce_str(raw, "rationale", fallback.rationale),
                source="llm",
            )
        )
    return resolved or fallback_items


def _build_planning_agent(
    topics: list[TopicSelection],
    snapshot_map: dict[str, SecuritySnapshot],
) -> list[AnalysisPlanItem]:
    fallback_items: list[AnalysisPlanItem] = []
    topic_payloads = []
    for topic in topics:
        snapshot = snapshot_map[topic.symbol]
        focus = _focus_priority(snapshot)
        keywords = _research_keywords(snapshot)
        fallback_items.append(
            AnalysisPlanItem(
                symbol=topic.symbol,
                name=topic.name,
                focus_priority=focus,
                keywords=keywords,
            )
        )
        topic_payloads.append(
            {
                "symbol": topic.symbol,
                "name": topic.name,
                "rationale": topic.rationale,
                "volatility_30d": snapshot.risk.volatility_30d,
                "roe": snapshot.fundamentals.roe,
                "per": snapshot.fundamentals.per,
                "rsi": snapshot.technicals.rsi,
            }
        )

    prompt = (
        "너는 투자 리서치 팀장이야. 추천된 종목들에 대해 심층 리포트를 작성하기 위한 계획을 세워줘. "
        "각 종목별로 '거시 경제 환경', '기업 실적 전망', '차트 흐름 분석' 중 어디에 비중을 두어 조사할지 "
        "우선순위를 정해줘. 또한 리서치 에이전트가 찾아와야 할 핵심 키워드들을 종목별로 3개씩 뽑아줘.\n\n"
        "종목 데이터:\n{topics}"
    ).format(topics=json.dumps(topic_payloads, ensure_ascii=False))
    response = _call_json_agent("planning", prompt, {"plan": [asdict(item) for item in fallback_items]})
    plan = response.get("plan") if response else None
    if not isinstance(plan, list):
        return fallback_items

    resolved: list[AnalysisPlanItem] = []
    for raw, fallback in zip(plan[: len(fallback_items)], fallback_items):
        resolved.append(
            AnalysisPlanItem(
                symbol=_coerce_str(raw, "symbol", fallback.symbol),
                name=_coerce_str(raw, "name", fallback.name),
                focus_priority=_coerce_str(raw, "focus_priority", fallback.focus_priority),
                keywords=_coerce_list(raw, "keywords", fallback.keywords)[:3],
                source="llm",
            )
        )
    return resolved or fallback_items


def _build_research_agent(
    request: InvestmentRequest,
    plan: list[AnalysisPlanItem],
    snapshot_map: dict[str, SecuritySnapshot],
) -> list[ResearchFinding]:
    fallback_items: list[ResearchFinding] = []
    plan_payloads = []
    for item in plan:
        snapshot = snapshot_map[item.symbol]
        facts = [
            f"시장: {snapshot.market}",
            f"현재가: {_fmt_num(snapshot.price)} {snapshot.currency}",
            f"RSI: {_fmt_num(snapshot.technicals.rsi)} / MACD: {_fmt_num(snapshot.technicals.macd)}",
            f"ROE: {_fmt_num(snapshot.fundamentals.roe)} / PER: {_fmt_num(snapshot.fundamentals.per)}",
            f"30일 변동성: {_fmt_num(snapshot.risk.volatility_30d)}",
        ]
        if snapshot.notes:
            facts.extend(snapshot.notes[:2])
        flags = list(snapshot.risk.negative_news_flags)
        fallback_items.append(
            ResearchFinding(
                symbol=item.symbol,
                name=item.name,
                facts=facts,
                negative_news_flags=flags,
                sources=[],
            )
        )
        plan_payloads.append(
            {
                "symbol": item.symbol,
                "name": item.name,
                "focus_priority": item.focus_priority,
                "keywords": item.keywords,
                "negative_news_flags": flags,
                "notes": snapshot.notes,
            }
        )

    prompt = (
        "너는 전문 리서치 어시스턴트야. 제공된 키워드를 바탕으로 {market} 시장의 최신 뉴스, 공시, 증권사 리포트, "
        "어닝콜/실적 발표 문서를 우선 수집해줘. MCP 도구가 있으면 반드시 활용하고, 각 종목별로 출처 URL을 2개 이상 확보해. "
        "특히 최근 30일간의 변동성 이슈나 부정적 뉴스 플래그(negative_news_flags)가 있는지 집중 파악해서 "
        "사실 기반 데이터만 정리해. 출력 JSON에는 sources 배열(문자열 URL 목록)을 반드시 포함해.\n\n"
        "리서치 계획:\n{plan}"
    ).format(
        market=request.market,
        plan=json.dumps(plan_payloads, ensure_ascii=False),
    )
    response = _call_json_agent("research", prompt, {"research": [asdict(item) for item in fallback_items]})
    research = response.get("research") if response else None
    if not isinstance(research, list):
        return fallback_items

    resolved: list[ResearchFinding] = []
    for raw, fallback in zip(research[: len(fallback_items)], fallback_items):
        resolved.append(
            ResearchFinding(
                symbol=_coerce_str(raw, "symbol", fallback.symbol),
                name=_coerce_str(raw, "name", fallback.name),
                facts=_coerce_list(raw, "facts", fallback.facts),
                negative_news_flags=_coerce_list(raw, "negative_news_flags", fallback.negative_news_flags),
                sources=_coerce_list(raw, "sources", fallback.sources)[:5],
                source="llm",
            )
        )
    return resolved or fallback_items


def _build_insight_agent(
    request: InvestmentRequest,
    persona: InvestorPersona,
    recommendations: list[Recommendation],
    research: list[ResearchFinding],
    snapshot_map: dict[str, SecuritySnapshot],
) -> list[StockInsight]:
    research_map = {item.symbol: item for item in research}
    fallback_items: list[StockInsight] = []
    research_payloads = []
    for item in recommendations:
        snapshot = snapshot_map[item.symbol]
        finding = research_map[item.symbol]
        risks = list(item.warnings[:2]) or ["추가 모니터링 필요"]
        thesis = (
            f"{persona.risk_tolerance} 투자자에게 {item.name}는 {item.rationale} 관점에서 적합합니다. "
            f"기술 지표와 밸류에이션을 함께 보면 {request.duration} 대응에 유리한 후보입니다."
        )
        scenario = (
            f"{request.duration} 기준으로 진입가는 {item.entry_price or 'N/A'}, "
            f"목표가는 {item.target_price or 'N/A'}, 손절가는 {item.stop_loss_price or 'N/A'}로 관리합니다."
        )
        fallback_items.append(
            StockInsight(
                symbol=item.symbol,
                name=item.name,
                thesis=thesis,
                scenario=scenario,
                key_risks=risks + finding.negative_news_flags[:2],
            )
        )
        research_payloads.append(
            {
                "symbol": item.symbol,
                "name": item.name,
                "recommendation_reason": item.reason,
                "research_facts": finding.facts,
                "negative_news_flags": finding.negative_news_flags,
                "sources": finding.sources,
            }
        )

    prompt = (
        "너는 수석 포트폴리오 매니저야. 수집된 리서치 데이터와 사용자의 페르소나를 결합해줘. "
        "단순한 정보 나열이 아니라, '이 종목이 왜 지금 매수 적기인가?' 혹은 '어떤 리스크를 주의해야 하는가?'에 대한 "
        "날카로운 투자 인사이트를 도출해줘. 투자 기간({duration})에 맞춘 구체적인 대응 시나리오를 포함해야 해.\n\n"
        "페르소나:\n{persona}\n\n리서치 데이터:\n{research}"
    ).format(
        duration=request.duration,
        persona=json.dumps(asdict(persona), ensure_ascii=False),
        research=json.dumps(research_payloads, ensure_ascii=False),
    )
    response = _call_json_agent("insight", prompt, {"insights": [asdict(item) for item in fallback_items]})
    insights = response.get("insights") if response else None
    if not isinstance(insights, list):
        return fallback_items

    resolved: list[StockInsight] = []
    for raw, fallback in zip(insights[: len(fallback_items)], fallback_items):
        resolved.append(
            StockInsight(
                symbol=_coerce_str(raw, "symbol", fallback.symbol),
                name=_coerce_str(raw, "name", fallback.name),
                thesis=_coerce_str(raw, "thesis", fallback.thesis),
                scenario=_coerce_str(raw, "scenario", fallback.scenario),
                key_risks=_coerce_list(raw, "key_risks", fallback.key_risks),
                source="llm",
            )
        )
    return resolved or fallback_items


def _build_writing_agent(
    request: InvestmentRequest,
    persona: InvestorPersona,
    recommendations: list[Recommendation],
    insights: list[StockInsight],
    snapshot_map: dict[str, SecuritySnapshot],
) -> str:
    insights_map = {item.symbol: item for item in insights}
    fallback_report = _fallback_markdown_report(request, persona, recommendations, insights)

    recommendation_payloads = []
    for item in recommendations:
        snapshot = snapshot_map[item.symbol]
        insight = insights_map[item.symbol]
        recommendation_payloads.append(
            {
                "symbol": item.symbol,
                "name": item.name,
                "current_price": snapshot.price,
                "currency": snapshot.currency,
                "entry_price": item.entry_price,
                "target_price": item.target_price,
                "stop_loss_price": item.stop_loss_price,
                "expected_return_pct": item.expected_return_pct,
                "thesis": insight.thesis,
                "scenario": insight.scenario,
                "key_risks": insight.key_risks,
            }
        )

    prompt = (
        "너는 금융 전문 작가야. 인사이트 에이전트가 도출한 내용을 바탕으로 최종 투자 전략 리포트를 작성해줘. "
        "전문적이면서도 사용자가 이해하기 쉬운 톤앤매너를 유지해. 종목별 진입가, 목표가, 손절가를 명확히 표기하고, "
        "'매매 가이드' 섹션을 만들어 구체적인 실행 방안을 제안해줘. 출력 형식은 지정된 마크다운 템플릿을 따라야 해.\n\n"
        "사용자 정보:\n{request_payload}\n\n페르소나:\n{persona}\n\n종목 인사이트:\n{recommendations}"
    ).format(
        request_payload=json.dumps(asdict(request), ensure_ascii=False),
        persona=json.dumps(asdict(persona), ensure_ascii=False),
        recommendations=json.dumps(recommendation_payloads, ensure_ascii=False),
    )
    response = _call_text_agent("writing", prompt)
    return response.strip() if response else fallback_report


def _build_verification_agent(
    request: InvestmentRequest,
    recommendations: list[Recommendation],
    snapshots: list[SecuritySnapshot],
    markdown_report: str,
) -> VerificationResult:
    snapshot_map = {item.symbol: item for item in snapshots}
    issues: list[str] = []
    corrections: list[str] = []
    for item in recommendations:
        snapshot = snapshot_map[item.symbol]
        if item.current_price is not None and snapshot.price is not None and round(item.current_price, 2) != round(snapshot.price, 2):
            issues.append(f"{item.symbol} 현재가 불일치")
            corrections.append(f"{item.symbol} 현재가는 {snapshot.price} 기준으로 표기해야 합니다.")
        if request.propensity == "안정추구형" and item.risk_level == "높음":
            issues.append(f"{item.symbol} 추천이 보수적 성향과 충돌")
            corrections.append(f"{item.symbol} 비중 축소 또는 제외 검토가 필요합니다.")

    fallback = VerificationResult(
        passed=not issues,
        issues=issues or ["검증 기준 내 주요 불일치 없음"],
        corrections=corrections,
    )

    verification_payload = {
        "request": asdict(request),
        "recommendations": [asdict(item) for item in recommendations],
        "snapshots": [_snapshot_payload(item) for item in snapshots[: len(recommendations)]],
        "report_excerpt": markdown_report[:4000],
        "fallback": asdict(fallback),
    }
    prompt = (
        "너는 금융 컴플라이언스 감찰관이야. 작성된 리포트의 수치들이 원본 데이터(SecuritySnapshot)와 일치하는지 검증해줘. "
        "특히 현재가, PER, RSI 등의 지표가 뒤바뀌지 않았는지, 추천 로직이 사용자의 위험도 설정과 충돌하지 않는지 확인해. "
        "오류가 있다면 수정 제안을 남기거나 직접 교정해줘.\n\n검증 데이터:\n{payload}"
    ).format(payload=json.dumps(verification_payload, ensure_ascii=False))
    response = _call_json_agent("verification", prompt, asdict(fallback))
    return VerificationResult(
        passed=_coerce_bool(response, "passed", fallback.passed),
        issues=_coerce_list(response, "issues", fallback.issues),
        corrections=_coerce_list(response, "corrections", fallback.corrections),
        source="llm" if response else fallback.source,
    )


def _rule_based_persona(request: InvestmentRequest) -> InvestorPersona:
    risk_tolerance = {
        "안정추구형": "원금 방어를 우선하는 보수형",
        "중립형": "수익성과 방어력의 균형을 추구하는 균형형",
        "공격투자형": "높은 변동성을 감수하며 초과 수익을 노리는 적극형",
    }.get(request.propensity, "수익과 방어의 균형을 원하는 일반형")
    sector_interests = {
        "안정추구형": ["배당", "필수소비재", "대형 우량주"],
        "중립형": ["IT", "플랫폼", "헬스케어"],
        "공격투자형": ["AI", "반도체", "2차전지"],
    }.get(request.propensity, ["대형주", "성장주", "분산 ETF"])
    decision_values = {
        "단기": ["타이밍", "변동성 관리", "손절 규율"],
        "중기": ["추세 지속성", "실적 모멘텀", "리스크 대비 보상"],
        "장기": ["기업 체력", "복리 성장", "밸류에이션 지속 가능성"],
    }.get(request.duration, ["분산", "현금 관리", "리스크 점검"])
    summary = (
        f"이 사용자는 {risk_tolerance} 투자자이며, {request.market} 시장에서 "
        f"{request.duration} 관점의 기회를 찾고 있습니다. 관심 섹터는 "
        f"{', '.join(sector_interests)} 쪽으로 기울 가능성이 높고, 의사결정에서는 "
        f"{', '.join(decision_values)}를 중시할 확률이 큽니다."
    )
    return InvestorPersona(
        summary=summary,
        risk_tolerance=risk_tolerance,
        sector_interests=sector_interests,
        decision_values=decision_values,
    )


def _focus_priority(snapshot: SecuritySnapshot) -> str:
    if snapshot.risk.volatility_30d is not None and snapshot.risk.volatility_30d >= 35:
        return "차트 흐름 분석"
    if snapshot.fundamentals.roe is not None and snapshot.fundamentals.roe >= 12:
        return "기업 실적 전망"
    return "거시 경제 환경"


def _research_keywords(snapshot: SecuritySnapshot) -> list[str]:
    keywords = [snapshot.name, snapshot.symbol]
    if snapshot.fundamentals.roe is not None:
        keywords.append("earnings outlook")
    elif snapshot.technicals.rsi is not None:
        keywords.append("price momentum")
    else:
        keywords.append("market outlook")
    return keywords[:3]


def _fallback_markdown_report(
    request: InvestmentRequest,
    persona: InvestorPersona,
    recommendations: list[Recommendation],
    insights: list[StockInsight],
) -> str:
    insight_map = {item.symbol: item for item in insights}
    lines = [
        "# Multi-Agent Investment Report",
        "",
        "## Investor Persona",
        persona.summary,
        "",
        f"- Risk tolerance: {persona.risk_tolerance}",
        f"- Sector interests: {', '.join(persona.sector_interests)}",
        f"- Decision values: {', '.join(persona.decision_values)}",
        "",
        "## Trade Guide",
        f"- Market: {request.market}",
        f"- Duration: {request.duration}",
        f"- Propensity: {request.propensity}",
        "",
        "## Recommendations",
        "",
    ]
    for item in recommendations:
        insight = insight_map[item.symbol]
        lines.extend(
            [
                f"### {item.name} ({item.symbol})",
                f"- Insight: {insight.thesis}",
                f"- Entry: {item.entry_price}",
                f"- Target: {item.target_price}",
                f"- Stop loss: {item.stop_loss_price}",
                f"- Scenario: {insight.scenario}",
                f"- Risks: {', '.join(insight.key_risks)}",
                "",
            ]
        )
    return "\n".join(lines).strip()


def _snapshot_payload(snapshot: SecuritySnapshot) -> dict[str, Any]:
    return {
        "symbol": snapshot.symbol,
        "name": snapshot.name,
        "market": snapshot.market,
        "price": snapshot.price,
        "currency": snapshot.currency,
        "rsi": snapshot.technicals.rsi,
        "macd": snapshot.technicals.macd,
        "per": snapshot.fundamentals.per,
        "roe": snapshot.fundamentals.roe,
        "volatility_30d": snapshot.risk.volatility_30d,
        "negative_news_flags": snapshot.risk.negative_news_flags,
    }


def _call_json_agent(agent_name: str, prompt: str, fallback: dict[str, Any]) -> dict[str, Any]:
    text = _call_text_agent(
        agent_name,
        prompt,
        response_format={
            "type": "json_schema",
            "name": f"{agent_name}_response",
            "schema": {
                "type": "object",
                "additionalProperties": True,
            },
        },
    )
    if not text:
        return {}
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return fallback
    return value if isinstance(value, dict) else fallback


def _call_text_agent(
    agent_name: str,
    prompt: str,
    response_format: dict[str, Any] | None = None,
) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return ""

    payload: dict[str, Any] = {
        "model": _agent_model(agent_name),
        "input": [
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": "Return concise, high-signal output. If JSON is requested, return valid JSON only.",
                    }
                ],
            },
            {
                "role": "user",
                "content": [{"type": "input_text", "text": prompt}],
            },
        ],
    }
    mcp_tools, _, _ = _resolve_mcp_tools()
    tool_choice = _resolve_mcp_tool_choice()
    if mcp_tools:
        payload["tools"] = mcp_tools
    if tool_choice is not None:
        payload["tool_choice"] = tool_choice
    if response_format is not None:
        payload["text"] = {"format": response_format}

    body = _post_responses(payload, api_key)
    if body is None and mcp_tools:
        fallback_payload = dict(payload)
        fallback_payload.pop("tools", None)
        fallback_payload.pop("tool_choice", None)
        body = _post_responses(fallback_payload, api_key)
    if body is None:
        return ""

    output_text = body.get("output_text")
    if isinstance(output_text, str):
        return output_text

    for item in body.get("output", []):
        for content in item.get("content", []):
            text = content.get("text")
            if isinstance(text, str):
                return text
    return ""


def get_mcp_config_status() -> dict[str, Any]:
    tools, source, parse_error = _resolve_mcp_tools()
    labels: list[str] = []
    for item in tools:
        label = item.get("server_label")
        if isinstance(label, str) and label.strip():
            labels.append(label.strip())
    return {
        "enabled": bool(tools),
        "source": source,
        "tool_count": len(tools),
        "server_labels": labels,
        "tool_choice": _resolve_mcp_tool_choice(),
        "parse_error": parse_error,
    }


def _post_responses(payload: dict[str, Any], api_key: str) -> dict[str, Any] | None:
    try:
        response = requests.post(
            OPENAI_RESPONSES_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=45,
        )
        response.raise_for_status()
    except requests.RequestException:
        return None
    body = response.json()
    return body if isinstance(body, dict) else None


def _resolve_mcp_tools() -> tuple[list[dict[str, Any]], str | None, bool]:
    tools_text = os.getenv("AI_MCP_TOOLS_JSON", "").strip()
    if tools_text:
        try:
            parsed = json.loads(tools_text)
        except json.JSONDecodeError:
            return [], "AI_MCP_TOOLS_JSON", True
        if isinstance(parsed, list):
            tools = [item for item in parsed if isinstance(item, dict)]
            return tools, "AI_MCP_TOOLS_JSON", False
        return [], "AI_MCP_TOOLS_JSON", True

    servers_text = os.getenv("AI_MCP_SERVERS_JSON", "").strip()
    if servers_text:
        try:
            parsed = json.loads(servers_text)
        except json.JSONDecodeError:
            return [], "AI_MCP_SERVERS_JSON", True
        if not isinstance(parsed, list):
            return [], "AI_MCP_SERVERS_JSON", True
        return _build_mcp_tools(parsed), "AI_MCP_SERVERS_JSON", False

    file_path = os.getenv("AI_MCP_SERVERS_FILE", "").strip() or "mcp_servers.json"
    try:
        text = open(file_path, "r", encoding="utf-8").read().strip()
    except OSError:
        return [], None, False
    if not text:
        return [], "AI_MCP_SERVERS_FILE", False
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return [], "AI_MCP_SERVERS_FILE", True
    if not isinstance(parsed, list):
        return [], "AI_MCP_SERVERS_FILE", True
    return _build_mcp_tools(parsed), "AI_MCP_SERVERS_FILE", False


def _build_mcp_tools(parsed: list[Any]) -> list[dict[str, Any]]:
    tools: list[dict[str, Any]] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        server_url = item.get("server_url")
        server_label = item.get("server_label")
        if not isinstance(server_url, str) or not server_url.strip():
            continue
        if not isinstance(server_label, str) or not server_label.strip():
            continue
        tool: dict[str, Any] = {
            "type": "mcp",
            "server_url": server_url.strip(),
            "server_label": server_label.strip(),
        }
        authorization = item.get("authorization")
        if isinstance(authorization, str) and authorization.strip():
            tool["authorization"] = authorization.strip()
        headers = item.get("headers")
        if isinstance(headers, dict):
            tool["headers"] = headers
        allowed_tools = item.get("allowed_tools")
        if isinstance(allowed_tools, list):
            cleaned = [tool_name for tool_name in allowed_tools if isinstance(tool_name, str) and tool_name.strip()]
            if cleaned:
                tool["allowed_tools"] = cleaned
        tools.append(tool)
    return tools


def _resolve_mcp_tool_choice() -> Any:
    raw = os.getenv("AI_MCP_TOOL_CHOICE", "").strip()
    if not raw:
        return None
    lowered = raw.lower()
    if lowered in {"none", "auto", "required"}:
        return lowered
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _agent_model(agent_name: str) -> str:
    specific = os.getenv(f"AI_{agent_name.upper()}_MODEL", "").strip()
    if specific:
        return specific
    return os.getenv("AI_DEFAULT_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL


def _agent_model_map() -> dict[str, str]:
    names = [
        "persona",
        "topic_selection",
        "planning",
        "research",
        "insight",
        "writing",
        "verification",
    ]
    return {name: _agent_model(name) for name in names}


def _coerce_str(payload: dict[str, Any] | None, key: str, default: str) -> str:
    if not isinstance(payload, dict):
        return default
    value = payload.get(key)
    return value.strip() if isinstance(value, str) and value.strip() else default


def _coerce_list(payload: dict[str, Any] | None, key: str, default: list[str]) -> list[str]:
    if not isinstance(payload, dict):
        return default
    value = payload.get(key)
    if not isinstance(value, list):
        return default
    result = [item.strip() for item in value if isinstance(item, str) and item.strip()]
    return result or default


def _coerce_bool(payload: dict[str, Any] | None, key: str, default: bool) -> bool:
    if not isinstance(payload, dict):
        return default
    value = payload.get(key)
    return value if isinstance(value, bool) else default


def _fmt_num(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.2f}"
