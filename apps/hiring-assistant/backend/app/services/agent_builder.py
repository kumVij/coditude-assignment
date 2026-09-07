"""
Turns a recruiter's Job Description into a Hunar voice-agent configuration:
system prompt, introduction, and the structured result_schema the agent
should extract from the conversation.

This is intentionally template-based (no external LLM call) so the
assignment has zero extra API dependencies and works even if an LLM key
isn't configured. Swapping this for an LLM-generated prompt (e.g. via
the Anthropic API) is a one-function change - see the README "Next steps".
"""
from app.models.db_models import Job
from app.services.llm import generate_json


def build_agent_config(job: Job, round_number: int = 1) -> dict:
    generated = generate_json(
        f"Return JSON with keys agent_prompt, introduction, objective, result_prompt, result_schema. "
        f"Create a concise ethical recruiting voice-screen agent for round {round_number} of role {job.title}. "
        f"Job description: {job.description}. Must-have skills: {job.must_have_skills}. "
        f"Recruiter questions: {job.screening_questions}. Return JSON only."
    )
    if generated:
        return generated
    questions = [q.strip() for q in job.screening_questions.splitlines() if q.strip()]
    if not questions:
        questions = [
            "What is your total relevant experience for this role?",
            "What is your current notice period?",
            "What are your current and expected compensation (CTC)?",
            "Are you open to the work location / mode mentioned in the job description?",
        ]
    numbered_questions = "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))

    round_instruction = (
        "Focus on practical technical depth, architecture tradeoffs, and a concrete project example."
        if round_number == 2
        else "Focus on eligibility, motivation, communication, and core role requirements."
    )
    agent_prompt = f"""You are {{persona_name}}, a friendly and professional recruiting
screener calling on behalf of the hiring team for the role: {job.title}.

Role summary:
{job.description}

Must-have skills / requirements to probe for:
{job.must_have_skills or "See role summary above."}

Your goals for this call:
This is screening round {round_number}. {round_instruction}
- Confirm you are speaking with {{callee_name}}.
- Briefly explain you are calling for an initial phone screen for the {job.title} role.
- Ask the following screening questions, one at a time, and listen carefully to the answers:
{numbered_questions}
- Be conversational, not robotic. Acknowledge answers briefly before moving to the next question.
- If the candidate is not interested or not a fit, thank them politely and end the call.
- If the candidate asks about next steps, tell them the recruiting team will review and follow up
  within a few business days.
- Keep the call under 6 minutes.
"""

    introduction = (
        "Hi, am I speaking with {callee_name}? This is {persona_name} calling from the "
        f"recruiting team regarding your application for the {job.title} position. "
        "Do you have a couple of minutes for a quick phone screen?"
    )

    result_prompt = (
        "Analyze the conversation transcript and extract structured screening results. "
        "Be objective and base every field strictly on what the candidate actually said."
    )

    result_schema = {
        "reachable": "boolean - true if the candidate answered and engaged in conversation",
        "interested": "boolean - candidate expressed interest in proceeding",
        "relevant_experience_years": "string - candidate's stated relevant experience",
        "notice_period": "string - candidate's stated notice period",
        "current_ctc": "string - candidate's stated current compensation, if shared",
        "expected_ctc": "string - candidate's stated expected compensation, if shared",
        "location_mode_ok": "boolean - candidate is open to the stated work location/mode",
        "recommendation": "string - one of: STRONG_FIT, POSSIBLE_FIT, NOT_A_FIT, INCONCLUSIVE",
        "summary": "string - 2-3 sentence summary of the conversation for the recruiter",
    }

    return {
        "agent_prompt": agent_prompt,
        "introduction": introduction,
        "objective": f"Conduct screening round {round_number} for the {job.title} role and "
        "collect structured screening data for the recruiting team.",
        "result_prompt": result_prompt,
        "result_schema": result_schema,
    }
