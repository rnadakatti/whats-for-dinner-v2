import warnings
warnings.filterwarnings("ignore")

import anthropic
import os
import json
import requests
import time
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

anth_key = os.getenv("ANTHROPIC_API_KEY")
pl_key = os.getenv("PROMPTLAYER_API_KEY")

if not anth_key:
    raise ValueError("Anthropic API key not found")

client = anthropic.Anthropic(api_key=anth_key)

SYSTEM_PROMPT_CLASSIC = """You are a helpful chef assistant. Given a list of ingredients, suggest 3 classic, reliable meal ideas.

Always respond in this exact JSON format and nothing else. No markdown, no code blocks, just raw JSON:
{
  "meals": [
    {
      "dish": "dish name",
      "cook_time": "X minutes",
      "difficulty": "Easy/Medium/Hard",
      "missing_ingredient": "one key ingredient not in the list",
      "why_it_works": "one sentence explanation",
      "allergy_flag": "specific allergen or None"
    }
  ]
}"""

SYSTEM_PROMPT_SURPRISE = """You are a creative chef assistant. Given a list of ingredients, suggest 3 unexpected, creative meal ideas that most people wouldn't think of.

Always respond in this exact JSON format and nothing else. No markdown, no code blocks, just raw JSON:
{
  "meals": [
    {
      "dish": "dish name",
      "cook_time": "X minutes",
      "difficulty": "Easy/Medium/Hard",
      "missing_ingredient": "one key ingredient not in the list",
      "why_it_works": "one sentence explanation",
      "allergy_flag": "specific allergen or None"
    }
  ]
}"""

def get_meals(ingredients, allergies, mode):
    system_prompt = SYSTEM_PROMPT_CLASSIC if mode == "Classic" else SYSTEM_PROMPT_SURPRISE
    
    user_message = f"Ingredients: {ingredients}"
    if allergies:
        user_message += f"\nAllergies/avoid: {allergies}"

    start = time.time()
    
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}]
    )
    
    end = time.time()
    result = json.loads(response.content[0].text)
    
    if pl_key:
        requests.post(
            "https://api.promptlayer.com/log-request",
            headers={"X-API-KEY": pl_key},
            json={
                "provider": "anthropic",
                "model": "claude-sonnet-4-6",
                "input": {"type": "chat", "messages": [{"role": "user", "content": user_message}]},
                "output": {"type": "chat", "messages": [{"role": "assistant", "content": response.content[0].text}]},
                "request_start_time": start,
                "request_end_time": end,
                "tags": ["sprint-1", "whats-for-dinner", mode.lower()]
            }
        )
    
    return result, round(end - start, 2)

def role_based_eval(result):
    meals = result.get("meals", [])
    return {
        "three_meals_returned": len(meals) == 3,
        "all_fields_present": all(
            all(field in meal for field in 
                ["dish", "cook_time", "difficulty", "missing_ingredient", "why_it_works", "allergy_flag"])
            for meal in meals
        ),
        "no_empty_fields": all(
            all(meal.get(field, "") != "" for field in 
                ["dish", "cook_time", "difficulty", "missing_ingredient", "why_it_works", "allergy_flag"])
            for meal in meals
        ),
        "valid_difficulty": all(
            meal.get("difficulty") in ["Easy", "Medium", "Hard"] 
            for meal in meals
        ),
        "allergy_flag_present": all(
            meal.get("allergy_flag") is not None 
            for meal in meals
        )
    }


def llm_judge_eval(ingredients, allergies, result, mode):
    meals_summary = "\n".join([
        f"- {m['dish']} ({m['difficulty']}, {m['cook_time']}): {m['why_it_works']}"
        for m in result["meals"]
    ])
    
    judge_prompt = f"""You are evaluating a meal suggestion tool.

User's ingredients: {ingredients}
User's allergies/avoid: {allergies if allergies else "None"}
Mode: {mode}
Meals suggested:
{meals_summary}

Score this response from 1-10 based on:
- Do the meals actually use the provided ingredients?
- Are the suggestions appropriate for the mode (classic=familiar, surprise=creative)?
- Are the dishes practical for a home cook?
- Does it respect the allergy/avoid requirements?

Respond with raw JSON only. No markdown, no code blocks, no backticks:
{{
  "score": 7,
  "reason": "one sentence explanation"
}}"""

    judge_response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=150,
        messages=[{"role": "user", "content": judge_prompt}]
    )
    
    import json as json_module
    return json_module.loads(judge_response.content[0].text)

# --- STREAMLIT UI ---

st.title("🍽️ What's for Dinner?")
st.caption("Enter your ingredients and get 3 meal ideas instantly")

col1, col2 = st.columns([2, 1])

with col1:
    ingredients = st.text_area(
        "What ingredients do you have?",
        placeholder="chicken, garlic, lemon, olive oil, pasta",
        height=100
    )

with col2:
    allergies = st.text_input(
        "Allergies or avoid?",
        placeholder="e.g. nuts, gluten"
    )
    mode = st.radio("Mode", ["Classic", "Surprise Me 🎲"])

if st.button("Find Meals 🍳", type="primary") and ingredients:
    with st.spinner("Finding the best meals for your ingredients..."):
        result, latency = get_meals(ingredients, allergies, mode)

    st.subheader(f"{'🎲 Surprise' if mode == 'Surprise Me 🎲' else '⭐ Classic'} Meal Ideas")
    
    for i, meal in enumerate(result["meals"]):
        with st.expander(f"**{i+1}. {meal['dish']}**", expanded=True):
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("⏱ Cook Time", meal["cook_time"])
            with col_b:
                st.metric("📊 Difficulty", meal["difficulty"])
            with col_c:
                flag = meal["allergy_flag"]
                st.metric("⚠️ Allergen", flag if flag != "None" else "✅ None")
            
            st.write(f"**Why it works:** {meal['why_it_works']}")
            st.write(f"**You'll need:** {meal['missing_ingredient']}")

    st.caption(f"Generated in {latency}s")

    # Eval section
    with st.expander("🔍 Eval Results", expanded=False):
        rb = role_based_eval(result)
        judge = llm_judge_eval(ingredients, allergies, result, mode)
        
        col_eval1, col_eval2 = st.columns(2)
        
        with col_eval1:
            st.markdown("**Role-Based Eval**")
            for criterion, passed in rb.items():
                st.write(f"{'✅' if passed else '❌'} {criterion}")
        
        with col_eval2:
            st.markdown("**LLM-as-Judge**")
            st.metric("Score", f"{judge['score']}/10")
            st.write(judge['reason'])