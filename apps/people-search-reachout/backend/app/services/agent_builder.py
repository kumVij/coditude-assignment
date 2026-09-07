from app.models.db_models import SearchRequest
from app.services.llm import generate_json


def build_reachout_agent_config(search: SearchRequest) -> dict:
    generated = generate_json(
        f"Return JSON with keys agent_prompt, introduction, objective, result_prompt, result_schema. "
        f"Create an ethical warm sourcing agent for {search.job_title}. JD: {search.job_description}. "
        "Include a field willing_to_talk_to_recruiter and never pressure the person. Return JSON only."
    )
    if generated:
        return generated
    agent_prompt = f"""You are {{persona_name}}, a friendly talent-sourcing recruiter making a
warm outbound call about an open role: {search.job_title}.

Role summary:
{search.job_description}

Your goals for this call:
- Confirm you're speaking with {{callee_name}}, currently working at {{company}} as {{job_role}}.
- Briefly introduce the {search.job_title} opportunity and gauge genuine interest.
- If they're interested, ask:
  1. Are you currently open to new opportunities?
  2. What is your current notice period?
  3. What is your expected compensation range?
  4. Would you be open to a call with our recruiting team this week?
- If they are not interested, thank them politely, ask if you may reach out again in the future,
  and end the call gracefully. Never be pushy.
- Keep the tone warm, respectful of their time, and keep the call under 5 minutes.
"""

    introduction = (
        "Hi, am I speaking with {callee_name}? This is {persona_name}, a recruiter reaching out "
        f"about a {search.job_title} opportunity I thought might interest someone with your "
        "background at {company}. Do you have a couple of minutes?"
    )

    result_prompt = (
        "Analyze the conversation and extract structured sourcing results. Base every field "
        "strictly on what the candidate actually said."
    )

    result_schema = {
        "reachable": "boolean - true if the candidate answered and engaged",
        "open_to_opportunities": "boolean - candidate is open to exploring new roles",
        "notice_period": "string - candidate's stated notice period, if shared",
        "expected_compensation": "string - candidate's stated expected compensation, if shared",
        "willing_to_talk_to_recruiter": "boolean - agreed to a follow-up call",
        "recommendation": "string - one of: HIGH_PRIORITY, FOLLOW_UP, NOT_INTERESTED, UNREACHABLE",
        "summary": "string - 2-3 sentence summary of the conversation for the sourcing team",
    }

    return {
        "agent_prompt": agent_prompt,
        "introduction": introduction,
        "objective": f"Warmly source and gauge interest from passive candidates for the "
        f"{search.job_title} role, collecting structured sourcing data for the recruiting team.",
        "result_prompt": result_prompt,
        "result_schema": result_schema,
    }
