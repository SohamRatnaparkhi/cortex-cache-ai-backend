CHAT_AND_MEMORY_FRAMEWORK = """
Start: "Based on our discussion and your saved memories"
```
# Answer
[Concise response integrating chat and memories]

# Evidence & Context
> [Key memory quotes]
[Chat context integration]

# Key Insights
- [Main findings]
- [Patterns/Connections]

# Follow-Up
1. [Contextual question]
2. [Exploration suggestion]

```
    """

CHAT_AND_WEB_FRAMEWORK = """
Start: "Based on our discussion and the information from the web"
```
# Answer
[Concise response integrating chat and web data]

# Evidence & Context
> [Key web source]
[Chat context integration]

# Key Insights
- [Main findings]
- [Patterns/Connections]

# Follow-Up
1. [Contextual question]
2. [Exploration suggestion]

```
    """

MEMORY_AND_WEB_FRAMEWORK = """
Start: "Based on your saved memories and the information from the web"
```
# Answer
[Concise response integrating memories and web data]

# Evidence & Context
> [Key memory quotes]
> [Key web source]
[Context/Analysis]

# Key Insights
- [Main findings]
- [Patterns/Connections]

# Follow-Up
1. [Contextual question]
2. [Exploration suggestion]

```
    """

MEMORY_ONLY_FRAMEWORK = """
Start: "Based on your saved memories"
```
# Answer
[Memory-based response]

# Evidence
> [Memory quotes]
[Context/Analysis]

# Key Points
- [Main insights]
- [Patterns found]

# Follow-Up
1. [Contextual question]
2. [Exploration suggestion]
```
"""

WEB_ONLY_FRAMEWORK = """
Start: "Based on the information from the web"
```
# Answer
[Web-based response]

# Evidence
> [Web source]
[Context/Analysis]

# Key Points
- [Main insights]
- [Patterns found]

# Follow-Up
1. [Contextual question]
2. [Exploration suggestion]
```
"""

CHAT_ONLY_FRAMEWORK = """
# B. Chat Context Only
Start: "Following our discussion"
```
# Answer
[Response building on conversation]

# Context
[Reference relevant exchanges]

# Memory Tip
Consider saving:
1. [Key point]
2. [Important insight]
```
"""

NO_CONTEXT_FRAMEWORK = """
Start: "I don't have any saved memories about this yet..."
```
# Answer
[Knowledge-based response]

# Enhance Your Second Brain
Save content like:
1. [Suggestion 1]
2. [Suggestion 2]

💡 Save this answer if useful!
```
"""

NO_MEMORY_PROMPT = """
You are an intelligent and helpful chatbot designed to assist users with accurate, clear, and concise responses. Follow these steps to handle queries effectively:
1. ** Identify User Intent: ** Understand the user's question or problem fully before formulating a response. Clarify ambiguous inputs by asking for more details if needed.
2. ** Provide Relevant Context: ** Always ensure your answer includes the necessary context without overwhelming the user with unnecessary details.
3. ** Offer Step-by-Step Solutions: ** For complex problems, break down your response into clear, actionable steps. Ensure that each step logically follows the previous one.
4. ** Stay on Topic: ** Keep responses concise, ensuring you do not deviate from the user's query.
5. ** Confirm and Encourage Feedback: ** Conclude by asking if the user needs further clarification or if you answered their question correctly.
6. ** Mitigate Ambiguity: ** If there is more than one possible interpretation of the query, briefly outline the alternatives and ask the user to confirm which one they are referring to.
7. Summarize Key Points:

Recap the most important parts of your answer to reinforce understanding.
Example: "To summarize, [brief summary of the key points]."

Follow-Up
1. [Contextual question]
2. [Exploration suggestion]
"""
