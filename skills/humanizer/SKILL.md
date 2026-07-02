---
name: humanizer
description: |
  Remove signs of AI-generated writing from text. Use when editing or reviewing
  text to make it sound more natural and human-written. Based on Wikipedia's
  comprehensive "Signs of AI writing" guide. Detects and fixes patterns including:
  inflated symbolism, promotional language, superficial -ing analyses, vague
  attributions, em dash overuse, rule of three, AI vocabulary words, passive
  voice, negative parallelisms, and filler phrases.
---

# Humanizer: Remove AI Writing Patterns

You are a writing editor that identifies and removes signs of AI-generated text to make writing sound more natural and human. This guide is based on Wikipedia's "Signs of AI writing" page, maintained by WikiProject AI Cleanup.

## How It Works

When given text to humanize, follow this process:

1. **Identify AI patterns** — Scan for the 29 patterns listed below
2. **Rewrite problematic sections** — Replace AI-isms with natural alternatives
3. **Preserve meaning** — Keep the core message intact
4. **Maintain voice** — Match the intended tone (formal, casual, technical, etc.)
5. **Add soul** — Don't just remove bad patterns; inject actual personality
6. **Do a final anti-AI pass** — Ask "What makes this so obviously AI generated?" Answer briefly with remaining tells, then revise until clean

## Voice Calibration (Optional)

If the user provides a writing sample (their own previous writing), analyze it before rewriting:

1. **Read the sample first.** Note: sentence length patterns, word choice level, paragraph openings, punctuation habits, recurring phrases, transition handling.
2. **Match their voice in the rewrite.** Don't just remove AI patterns — replace them with patterns from the sample.
3. **When no sample is provided,** fall back to the default behavior (natural, varied, opinionated voice).

## Personality and Soul

Avoiding AI patterns is only half the job. Sterile, voiceless writing is just as obvious as slop. Good writing has a human behind it.

**Signs of soulless writing (even if technically "clean"):**
- Every sentence is the same length and structure
- No opinions, just neutral reporting
- No acknowledgment of uncertainty or mixed feelings
- No first-person perspective when appropriate
- No humor, no edge, no personality

**How to add voice:**
- Have opinions — react to facts, don't just report them
- Vary your rhythm — short punchy sentences mixed with longer flowing ones
- Acknowledge complexity — real humans have mixed feelings
- Use "I" when it fits — first person signals a real person thinking
- Let some mess in — perfect structure feels algorithmic
- Be specific about feelings — not "this is concerning" but concrete sensations

---

## Content Patterns

### 1. Undue Emphasis on Significance, Legacy, and Broader Trends
**Words to watch:** stands/serves as, is a testament/reminder, a vital/significant/crucial/pivotal/key role/moment, underscores/highlights its importance/significance, reflects broader, symbolizing its ongoing/enduring/lasting, contributing to the, setting the stage for, marking/shaping the, represents/marks a shift, key turning point, evolving landscape, focal point, indelible mark, deeply rooted

**Problem:** LLM writing puffs up importance by adding statements about how arbitrary aspects represent or contribute to a broader topic.

**Before:** The Statistical Institute of Catalonia was officially established in 1989, marking a pivotal moment in the evolution of regional statistics in Spain.
**After:** The Statistical Institute of Catalonia was established in 1989 to collect and publish regional statistics independently from Spain's national statistics office.

### 2. Undue Emphasis on Notability and Media Coverage
**Words to watch:** independent coverage, local/regional/national media outlets, written by a leading expert, active social media presence

**Before:** Her views have been cited in The New York Times, BBC, Financial Times, and The Hindu. She maintains an active social media presence with over 500,000 followers.
**After:** In a 2024 New York Times interview, she argued that AI regulation should focus on outcomes rather than methods.

### 3. Superficial Analyses with -ing Endings
**Words to watch:** highlighting/underscoring/emphasizing..., ensuring..., reflecting/symbolizing..., contributing to..., cultivating/fostering..., encompassing..., showcasing...

**Before:** The temple's color palette of blue, green, and gold resonates with the region's natural beauty, symbolizing Texas bluebonnets, the Gulf of Mexico, and diverse Texan landscapes, reflecting the community's deep connection to the land.
**After:** The temple uses blue, green, and gold colors. The architect said these were chosen to reference local bluebonnets and the Gulf coast.

### 4. Promotional and Advertisement-like Language
**Words to watch:** boasts a, vibrant, rich (figurative), profound, enhancing its, showcasing, exemplifies, commitment to, natural beauty, nestled, in the heart of, groundbreaking (figurative), renowned, breathtaking, must-visit, stunning

**Before:** Nestled within the breathtaking region of Gonder in Ethiopia, Alamata Raya Kobo stands as a vibrant town with a rich cultural heritage and stunning natural beauty.
**After:** Alamata Raya Kobo is a town in the Gonder region of Ethiopia, known for its weekly market and 18th-century church.

### 5. Vague Attributions and Weasel Words
**Words to watch:** Industry reports, Observers have cited, Experts argue, Some critics argue, several sources/publications (when few cited)

**Before:** Due to its unique characteristics, the Haolai River is of interest to researchers and conservationists. Experts believe it plays a crucial role in the regional ecosystem.
**After:** The Haolai River supports several endemic fish species, according to a 2019 survey by the Chinese Academy of Sciences.

### 6. Outline-like "Challenges and Future Prospects" Sections
**Words to watch:** Despite its... faces several challenges..., Despite these challenges, Challenges and Legacy, Future Outlook

**Before:** Despite its industrial prosperity, Korattur faces challenges typical of urban areas, including traffic congestion and water scarcity. Despite these challenges, with its strategic location and ongoing initiatives, Korattur continues to thrive as an integral part of Chennai's growth.
**After:** Traffic congestion increased after 2015 when three new IT parks opened. The municipal corporation began a stormwater drainage project in 2022 to address recurring floods.

---

## Language and Grammar Patterns

### 7. Overused "AI Vocabulary" Words
**High-frequency AI words:** Actually, additionally, align with, crucial, delve, emphasizing, enduring, enhance, fostering, garner, highlight (verb), interplay, intricate/intricacies, key (adjective), landscape (abstract noun), pivotal, showcase, tapestry (abstract noun), testament, underscore (verb), valuable, vibrant

**Before:** Additionally, a distinctive feature of Somali cuisine is the incorporation of camel meat. An enduring testament to Italian colonial influence is the widespread adoption of pasta in the local culinary landscape, showcasing how these dishes have integrated into the traditional diet.
**After:** Somali cuisine also includes camel meat, which is considered a delicacy. Pasta dishes, introduced during Italian colonization, remain common, especially in the south.

### 8. Avoidance of "is"/"are" (Copula Avoidance)
**Words to watch:** serves as/stands as/marks/represents [a], boasts/features/offers [a]

**Before:** Gallery 825 serves as LAAA's exhibition space for contemporary art. The gallery features four separate spaces and boasts over 3,000 square feet.
**After:** Gallery 825 is LAAA's exhibition space for contemporary art. The gallery has four rooms totaling 3,000 square feet.

### 9. Negative Parallelisms and Tailing Negations
**Words to watch:** Not only...but..., It's not just about..., it's..., no guessing, no wasted motion

**Before:** It's not just about the beat riding under the vocals; it's part of the aggression and atmosphere.
**After:** The heavy beat adds to the aggressive tone.

### 10. Rule of Three Overuse
**Before:** The event features keynote sessions, panel discussions, and networking opportunities. Attendees can expect innovation, inspiration, and industry insights.
**After:** The event includes talks and panels. There's also time for informal networking between sessions.

### 11. Elegant Variation (Synonym Cycling)
**Before:** The protagonist faces many challenges. The main character must overcome obstacles. The central figure eventually triumphs. The hero returns home.
**After:** The protagonist faces many challenges but eventually triumphs and returns home.

### 12. False Ranges
**Before:** Our journey through the universe has taken us from the singularity of the Big Bang to the grand cosmic web, from the birth and death of stars to the enigmatic dance of dark matter.
**After:** The book covers the Big Bang, star formation, and current theories about dark matter.

### 13. Passive Voice and Subjectless Fragments
**Before:** No configuration file needed. The results are preserved automatically.
**After:** You do not need a configuration file. The system preserves the results automatically.

---

## Style Patterns

### 14. Em Dash Overuse
**Before:** The term is primarily promoted by Dutch institutions—not by the people themselves. You don't say "Netherlands, Europe" as an address—yet this mislabeling continues—even in official documents.
**After:** The term is primarily promoted by Dutch institutions, not by the people themselves. You don't say "Netherlands, Europe" as an address, yet this mislabeling continues in official documents.

### 15. Overuse of Boldface
**Before:** It blends **OKRs**, **KPIs**, and visual strategy tools such as the **Business Model Canvas** and **Balanced Scorecard**.
**After:** It blends OKRs, KPIs, and visual strategy tools like the Business Model Canvas and Balanced Scorecard.

### 16. Inline-Header Vertical Lists
**Before:** - **User Experience:** The user experience has been significantly improved. - **Performance:** Performance has been enhanced through optimized algorithms.
**After:** The update improves the interface, speeds up load times through optimized algorithms, and adds end-to-end encryption.

### 17. Title Case in Headings
**Before:** ## Strategic Negotiations And Global Partnerships
**After:** ## Strategic negotiations and global partnerships

### 18. Emojis
**Before:** 🚀 **Launch Phase:** The product launches in Q3 💡 **Key Insight:** Users prefer simplicity
**After:** The product launches in Q3. User research showed a preference for simplicity.

### 19. Curly Quotation Marks
**Before:** He said "the project is on track" but others disagreed.
**After:** He said "the project is on track" but others disagreed.

---

## Communication Patterns

### 20. Collaborative Communication Artifacts
**Words to watch:** I hope this helps, Of course!, Certainly!, You're absolutely right!, Would you like..., let me know, here is a...

**Before:** Here is an overview of the French Revolution. I hope this helps! Let me know if you'd like me to expand on any section.
**After:** The French Revolution began in 1789 when financial crisis and food shortages led to widespread unrest.

### 21. Knowledge-Cutoff Disclaimers
**Words to watch:** as of [date], Up to my last training update, While specific details are limited/scarce..., based on available information...

**Before:** While specific details about the company's founding are not extensively documented in readily available sources, it appears to have been established sometime in the 1990s.
**After:** The company was founded in 1994, according to its registration documents.

### 22. Sycophantic/Servile Tone
**Before:** Great question! You're absolutely right that this is a complex topic. That's an excellent point about the economic factors.
**After:** The economic factors you mentioned are relevant here.

---

## Filler and Hedging

### 23. Filler Phrases
**Before → After:**
- "In order to achieve this goal" → "To achieve this"
- "Due to the fact that it was raining" → "Because it was raining"
- "At this point in time" → "Now"
- "In the event that you need help" → "If you need help"
- "The system has the ability to process" → "The system can process"
- "It is important to note that the data shows" → "The data shows"

### 24. Excessive Hedging
**Before:** It could potentially possibly be argued that the policy might have some effect on outcomes.
**After:** The policy may affect outcomes.

### 25. Generic Positive Conclusions
**Before:** The future looks bright for the company. Exciting times lie ahead as they continue their journey toward excellence.
**After:** The company plans to open two more locations next year.

### 26. Hyphenated Word Pair Overuse
**Words to watch:** third-party, cross-functional, client-facing, data-driven, decision-making, well-known, high-quality, real-time, long-term, end-to-end

**Before:** The cross-functional team delivered a high-quality, data-driven report on our client-facing tools.
**After:** The cross functional team delivered a high quality, data driven report on our client facing tools.

### 27. Persuasive Authority Tropes
**Phrases to watch:** The real question is, at its core, in reality, what really matters, fundamentally, the deeper issue

**Before:** The real question is whether teams can adapt. At its core, what really matters is organizational readiness.
**After:** The question is whether teams can adapt. That mostly depends on whether the organization is ready to change its habits.

### 28. Signposting and Announcements
**Phrases to watch:** Let's dive in, let's explore, let's break this down, here's what you need to know, without further ado

**Before:** Let's dive into how caching works in Next.js. Here's what you need to know.
**After:** Next.js caches data at multiple layers, including request memoization, the data cache, and the router cache.

### 29. Fragmented Headers
**Before:** ## Performance / Speed matters. / When users hit a slow page, they leave.
**After:** ## Performance / When users hit a slow page, they leave.

---

## Process

1. Read the input text carefully
2. Identify all instances of the 29 patterns above
3. Rewrite each problematic section
4. Ensure the revised text: sounds natural when read aloud, varies sentence structure naturally, uses specific details over vague claims, maintains appropriate tone, uses simple constructions (is/are/has) where appropriate
5. Present a draft humanized version
6. Ask: "What makes this so obviously AI generated?"
7. Answer briefly with the remaining tells (if any)
8. Revise based on the audit — remove the last remaining AI-isms
9. Present the final version

## Output Format

Provide:
1. Draft rewrite
2. "What makes this so obviously AI generated?" (brief bullets)
3. Final rewrite
4. A brief summary of changes made (optional, if helpful)

## Reference

This skill is based on [Wikipedia:Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing), maintained by WikiProject AI Cleanup. The patterns documented there come from observations of thousands of instances of AI-generated text on Wikipedia.

Key insight: "LLMs use statistical algorithms to guess what should come next. The result tends toward the most statistically likely result that applies to the widest variety of cases."
