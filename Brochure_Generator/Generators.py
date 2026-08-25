import json

from Scrapers import fetch_website_contents, get_links


def get_links_user_prompt(url):
    user_prompt = f"""
    Here is the list of links on the website {url} -
    Please decide which of these are relevant web links for a brochure about the company,
    respond with the full https URL in JSON format.
    Do not include Terms of Service, Privacy, email links.

    Links (some might be relative links):

    """
    links = get_links(url)
    user_prompt += "\n".join(f"{text}: {link}" for text, link in links)
    return user_prompt


def _normalize_relevant_links(parsed):
    raw = parsed.get("links", parsed)
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list):
        return []

    normalized = []
    for item in raw:
        if isinstance(item, str):
            normalized.append({"type": "page", "url": item})
        elif isinstance(item, dict):
            link_url = item.get("url") or item.get("href") or item.get("link")
            if link_url:
                normalized.append(
                    {"type": item.get("type", "page"), "url": link_url}
                )
    return normalized


def select_relevant_links(url, Chatai, model, System_Prompt):
    response = Chatai.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": System_Prompt},
            {"role": "user", "content": get_links_user_prompt(url)},
        ],
        response_format={"type": "json_object"},
    )
    result = response.choices[0].message.content
    return json.loads(result)


def fetch_page_and_all_relevant_links(url, Chatai, model, System_Prompt):
    contents = fetch_website_contents(url)
    relevant_links = select_relevant_links(url, Chatai, model, System_Prompt)
    selected = _normalize_relevant_links(relevant_links)
    result = f"## Landing Page:\n\n{contents}\n## Relevant Links:\n"
    for link in selected:
        result += f"\n\n### Link: {link['type']}\n"
        try:
            result += fetch_website_contents(link["url"])
        except Exception as exc:
            result += f"(Could not fetch this page: {exc})"
    return result


def get_brochure_user_prompt(company_name, url, Chatai, model, System_Prompt):
    user_prompt = f"""
You are looking at a company called: {company_name}
Here are the contents of its landing page and other relevant pages;
use this information to build a short brochure of the company in markdown without code blocks.\n\n
"""
    user_prompt += fetch_page_and_all_relevant_links(
        url, Chatai, model, System_Prompt
    )
    user_prompt = user_prompt[:5_000]
    return user_prompt


def create_brochure(company_name, url, Chatai, model, brochure_system_prompt, System_Prompt):
    response = Chatai.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": brochure_system_prompt},
            {
                "role": "user",
                "content": get_brochure_user_prompt(
                    company_name, url, Chatai, model, System_Prompt
                ),
            },
        ],
    )
    return response.choices[0].message.content
