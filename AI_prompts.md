# AI Prompts — Homework 4

Prompts sent to Claude (Claude Code) during this assignment, copied word for word, typos included. Each problem lists its number and title, the prompt, a follow-up prompt only if one was sent, and one sentence on what the first prompt was missing.

---

## Problem 1: Vibe coder prompts

**My prompt:**

> Today we will be working in homework 4 folder. Keep all work inside it.
> Create AI_prompts.md to record the prompts I send you throughout this assignment.
> For each problem we work on, I need it to include, The problem number and title, My actual prompt, A follow-up prompt if I give one, plus one sentence explaining what was missing after the first prompt.
>
> Start with Problem 1 here: remember to log this: Vibe coder prompts, and record this message. Add later sections as we reach those problems. Don’t invent prompts or follow-ups.
> For now, only set up the prompt log. We’ll build the project one question at a time. Also just like homework 3, we will be using claude to build it. but the api key will still be that chatgpt one from previous assignment since this is allowed

**Follow-up prompt:** None.

**What was missing after the first prompt:** N/A (no follow-up prompt was sent).

---

## Problem 2: Analyze database

**My prompt:**

> Here is problem 2: Look through data/campus_customs.db and help me understand its tables and fields, especially catalogue, inventory, and users.
>
> Start output/harness.md. For each table, list its fields and briefly explain why each field matters for the shop or chatbot. Also explain how the tables connect. Use what’s actually in the database and leave the database unchanged.
>
> Keep this concise because we’ll add more to the harness later. Log this prompt under Problem 2 in AI_prompts.md, and give me a short summary of what you found.
>
> I just put the data into AI foundation homework 4 folder

**Follow-up prompt:**

> I forgot to say, unzip the data as instructed

*(Sent with a screenshot of the assignment's Data section, which says to unzip `data.zip` so you have `data/campus_customs.db` and `data/products/`.)*

**What was missing after the first prompt:** The first prompt didn't say to set up the data the way the assignment instructs, so it was still in a `data-3` folder instead of `data/`, where the prompt and the assignment expect it.

---

## Problem 3: Build the Campus Customs website

**My prompt:**

> Here is problem 3: Build the Campus Customs website in homework 4 using React, Vite, and TypeScript. Add a top navigation bar with Home, Products, About Us, Log in, and Create account.
>
> Look at yalebulldogblue.com for the brand’s style and company information. Write original wording for Home and About Us rather than copying the site. Make the pages attractive and easy to use.
>
> On Products, show the actual catalogue items with their database image paths, names, prices, and short descriptions. Each card should open its own product page with a large image beside the full description, price, and available sizes and stock.
>
> Use a simple FastAPI app in backend/main.py to read the database and serve products and images. Leave the existing data unchanged.
>
> Add a floating chat panel in the bottom right. It can be a placeholder for now, ready to connect to the backend later. Keep Log in and Create account as basic page layouts at this stage.
>
> Run the site locally and check that navigation, product images, and individual product pages work. Log this

**Follow-up prompt:** None.

**What was missing after the first prompt:** N/A (no follow-up prompt was sent).

---

## Problem 4: Create account and login in

**My prompt:**

> Here is problem 4: Make the Create account and Log in pages work with the FastAPI backend.
> For a new account, collect first name, last name, email, password, and password confirmation. Save the account in the users table with a securely hashed password. Log in should use email and password, keep the user signed in as they browse, and provide a logout option. Show clear messages for invalid details or an email already registered.
> Make sure the existing test account works:
>
> * Email: [test@campuscustoms.yale.edu](mailto:test@campuscustoms.yale.edu)
> * Password: password
>
> Also create a new test account and confirm it can log in. Check that incorrect passwords are rejected. Keep passwords and their hashes out of chatbot messages and API responses, and leave the catalogue and inventory unchanged.
> Update output/harness.md with a short explanation of how authentication works, what user information is stored, and how passwords are protected.  btw the name for this is called Create account and login in, save to AI_prompts.md.

**Follow-up prompt:** None.

**What was missing after the first prompt:** N/A (no follow-up prompt was sent).

---

## Problem 5: PydanticAI agent backend

**My prompt:**

> Here is problem 5: Connect the website’s chat panel to a real PydanticAI shop agent through FastAPI. Use the Claude authentication setup we already agreed on for AI calls, while keeping PydanticAI as the agent framework.
> Keep the API app in backend/main.py, with these supporting files:
>
> * backend/prompts/prompt.md for the system prompt.
> * backend/agent.py for creating and running the agent.
> * backend/tools.py for its tools.
> * backend/models.py for structured chat replies and product cards.
>
> Add a chat route and replace the frontend’s placeholder response with the agent’s actual reply. Keep the existing product and login features working.
> Give the agent a friendly Campus Customs voice and basic safety rules. It should use verified information for product claims, be honest when information is unavailable, and protect passwords and private account details. We’ll expand its tools and safety rules in later problems.
> Make sure the backend can run from the backend folder with uvicorn main --reload --port 8000. You can keep port 8001 for the current preview while 8000 is occupied.
> Test a real message through the website. Update output/harness.md to explain the frontend-to-backend connection and how the agent loads its prompt and model. Log this under Problem 5 — PydanticAI agent backend in AI_prompts.md.

**Follow-up prompt:** None.

**What was missing after the first prompt:** N/A (no follow-up prompt was sent).

---

## Problem 6: Tools: product info and stock

**My prompt:**

> Here is problem 6: Build on the tools you added in Problem 5 so the chatbot can look up product descriptions, prices, and exact stock quantities, including stock for a specific size.
>
> Use data/campus_customs.db for these answers. The agent should call the lookup tools rather than guess prices or quantities, and clearly say when a size is out of stock. Keep these tools read-only.
>
> Update backend/tools.py as needed, expand backend/prompts/prompt.md with when to use the tools, and add or update the structured return types in backend/models.py.
>
> Test description, price, and size-specific stock questions through the website, including an out-of-stock example. Compare the answers with the database.
>
> Update output/harness.md to list each tool and briefly explain the fields in its lookup results and why you chose them. name is called" Tools: product info and stock" in AI_prompts.md.

**Follow-up prompt:** None.

**What was missing after the first prompt:** N/A (no follow-up prompt was sent).

---

## Problem 7: Chat search that updates the page

**My prompt:**

> Here is problem 7: Make chat searches update the main website page with matching products. For example, when I ask “What hoodies do you have?”, the agent should search the catalogue and show the results as product cards on the page.
>
> Build on the existing search tool and chat replies. Return structured product matches through FastAPI so the frontend can display their images, names, prices, and short descriptions. Make the results visible in the main page area, beyond the cards already inside the chat panel.
>
> Each result card should open the existing single-product page with its large image and full information. Show a clear message when there are no matches.
>
> Test a few searches through the website and click the resulting cards to confirm they open the correct products.
>
> Update backend/prompts/prompt.md and output/harness.md to explain how chat searches produce results on the page. the name for this one is called Chat search that updates the page, log in AI_prompts.md.

**Follow-up prompt:** None.

**What was missing after the first prompt:** N/A (no follow-up prompt was sent).

---

## Problem 8: Customer memory

**My prompt:**

> Here is problem 8: Add customer memory to the chatbot. When someone is logged in, save their conversation in the database and reload it when they return, so both the chat panel and the agent can continue that conversation. Reuse the existing chat-history table if it fits.
>
> Give the agent the current shopper’s name and email through its dependencies or context. Get their identity from the logged-in session, and keep each customer’s history separate. Passwords and other customers’ details should stay inaccessible.
>
> Also pass the current page context. On a product page, the agent should know which item “this” refers to—for example, “Do you have this in pink?” It should check the actual product information before answering.
>
> Guests should still be able to chat, but their history doesn’t need to be saved. On logout or account changes, clear the previous shopper’s conversation from the screen.
>
> Test that history returns after refreshing and logging back in, that another account sees only its own history, and that product-page questions refer to the right item.
>
> Update the agent prompt as needed and document history storage, customer fields, and page context in output/harness.md. The name is called Customer memory, log in AI_prompts.md.

**Follow-up prompt:** None.

**What was missing after the first prompt:** N/A (no follow-up prompt was sent).

---

## Problem 9: Usability improvements

**My prompt:**

> Here is problem 9: Improve the shop with two new frontend usability improvements and two new agent or backend usability improvements.
>
> Review what’s already built and choose practical additions. The frontend changes should make shopping easier or the interface clearer. The agent or backend changes should improve answers, reliability, safety, speed, or cost. Choose improvements beyond the features we completed in earlier problems.
>
> Start output/usability.md before or as you build. Clearly label the four improvements, explain what each adds, and briefly say why it helps a Campus Customs shopper or the business. Keep the final write-up consistent with what you actually implement.
>
> Test all four improvements in the running app and check that the existing shop, login, chat, and customer memory still work. Give me a short summary of the changes and checks.
>
> The name is called Usability improvements, log in AI_prompts.md.

**Follow-up prompt:** None.

**What was missing after the first prompt:** N/A (no follow-up prompt was sent).

---

## Problem 10: Style the website

**My prompt:**

> Here is problem 10: Give the website a creative design polish so it feels like a real Campus Customs storefront. Build on the existing Yale-inspired style and make a noticeable improvement to the overall presentation.
>
> Choose a coherent visual direction and refine the fonts, colors, spacing, headings, product cards, product pages, and chat panel. Add some distinctive design touches and subtle motion where they help the experience. Keep the products easy to browse, the text readable, and the layout comfortable on phones.
>
> Keep all existing features working, including search results, size filters, login, and customer memory. Preserve the original product images and database information.
>
> Check the finished design in the browser at desktop and phone sizes.
>
> Write a short, concrete output/design.md explaining what you changed and why those choices should encourage customers to explore the shop and feel confident about its products. log this one name is Style the website, and log in AI_prompts.md.

**Follow-up prompt:** None.

**What was missing after the first prompt:** N/A (no follow-up prompt was sent).

---

## Problem 11: Site testing (app check)

**My prompt:**

> Here is problem 11: Test the running website and create output/app_check.html to show the results.
> Capture clear screenshots of:
>
> 1. A chat question about an item’s stock and price, with the answer checked against the database.
> 2. A category question, such as asking for hoodies, that makes matching product cards appear on the main page.
> 3. One usability improvement from Problem 9.
>
> Give each check a heading, its screenshot, and one or two sentences explaining what the image proves. Use actual screenshots from the running app.
> Save the images in output/app_check_images/ and reference them with relative paths, such as app_check_images/inventory.png. Make sure app_check.html opens correctly by double-clicking it and that all images display without the app running.
> This one is called Site testing (app check), log into AI_prompts.md.

**Follow-up prompt:** None.

**What was missing after the first prompt:** N/A (no follow-up prompt was sent).

---

## Problem 12: Audit trail, safety, finish harness

**My prompt:**

> Here is problem 12:
> Keep an append-only output/audit_trail.json that records each agent run: time, tool names, short argument and result summaries, and why the run stopped. Preserve earlier entries across runs and restarts. Record errors and cached replies honestly, and keep passwords, tokens, secrets, and private customer details out of the log.
> Review backend/prompts/prompt.md and strengthen the shop’s safety rules: use database evidence for product claims, protect customer information, keep each account’s history separate, and stay within the tools’ allowed abilities.
> Finish output/harness.md so it explains the actual implementation:
>
> * The fields in backend/models.py and why they were chosen.
> * Each tool and what the agent can do.
> * Safety rules, distinguishing prompt instructions from checks enforced by code.
> * The model and authentication setup, loop limits, result caps, and how to run the frontend and backend.
>
> Document the limits actually in place, and add reasonable bounds if any are missing. Keep the explanation clear and concise.
> Test several runs to confirm the audit grows without losing earlier entries, check the safety rules, and confirm existing features still work. Log this Audit trail, safety, finish harness in AI_prompts.md.

**Follow-up prompt:** None.

**What was missing after the first prompt:** N/A (no follow-up prompt was sent).

---

## Problem 13: Push to GitHub and submit the URL

**My prompt:**

> Here is problem 13: prep this for submission in a folder named hw4, keeping the working homework 4 project intact.
>
> Include the frontend and backend source, dependency files, AI_prompts.md, README.md, .gitignore, and .env.example with placeholders only. Include all required output files: harness.md, design.md, usability.md, app_check.html, app_check_images/, and audit_trail.json. Confirm the harness is finished.
>
> Exclude the real .env, database and its backups, original product images, installed dependencies, and local preview settings. Keep the app-check screenshots included. Check that no credentials or private customer information will be published.
>
> Update README.md with instructions for installing dependencies, placing the separate data pack, configuring the grader’s own Claude authentication, and running the frontend and backend. Verify the submission works with those instructions and that the screenshot report opens correctly. I have attacked the info it needs to be in the pic.
>
> Log this under Problem 13 — Push to GitHub and submit the URL. Create a public GitHub repository and push the submission using my GitHub account. If GitHub access is missing, tell me what I need to connect. Give me the final repository URL and confirm the required files are present.

*(Sent with a screenshot of the assignment's expected file layout: `hw4/` with `AI_prompts.md`, `requirements.txt`, `.env.example`, `.gitignore`, `README.md`, `frontend/`, `backend/` (`main.py`, `agent.py`, `models.py`, `tools.py`, `prompts/prompt.md`) and `output/` (`harness.md`, `design.md`, `usability.md`, `app_check.html`, `app_check_images/`, `audit_trail.json`), plus a local-only `data/` pack with `campus_customs.db` and `products/` that is not in git.)*

**Follow-up prompt:** None.

**What was missing after the first prompt:** N/A (no follow-up prompt was sent).
