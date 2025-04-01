# Browser Operator Agent

This project implements an operator agent that controls a browser using Playwright and GPT-4o. The agent can perform various actions like clicking, typing, scrolling, and more to accomplish goals specified by the user.

## Features

- Navigate to websites
- Click, double-click, scroll, type, wait, move, keypress, drag
- Take screenshots
- Analyze web pages using GPT-4o to determine next actions
- Complete goals autonomously

## Requirements

- Python 3.8+
- Playwright
- OpenAI API key

## Installation

1. Clone this repository
2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```
3. Install Playwright browsers:
   ```
   python -m playwright install
   ```

## Usage

Set your OpenAI API key as an environment variable:

```bash
export OPENAI_API_KEY=your_api_key_here
```

Run the agent with a specific goal:

```bash
python main.py --goal "Add Nike shoes to an Amazon shopping cart"
```

For better results, you can specify a starting URL:

```bash
python main.py --goal "Add Nike shoes to a shopping cart" --start-url "https://www.amazon.com"
```

Additional options:
```bash
python main.py --goal "Your goal here" --max-steps 30 --api-key your_api_key --start-url "https://example.com"
```

## How It Works

1. The agent receives a goal (e.g., "Add Nike shoes to an Amazon shopping cart")
2. It takes an initial action (usually navigating to a website)
   - If a starting URL is provided, it navigates there automatically
   - Otherwise, it analyzes the current page and determines where to go
3. It takes a screenshot of the current page
4. GPT-4o analyzes the screenshot and determines the next action
5. The agent performs the action (click, type, etc.)
6. This process continues until the goal is completed or max steps is reached

## Example Goals

- "Search for Python programming on Google" (--start-url "https://www.google.com")
- "Add Nike shoes to an Amazon shopping cart" (--start-url "https://www.amazon.com")
- "Check the weather in New York on weather.com" (--start-url "https://weather.com")
- "Log in to GitHub with my credentials" (--start-url "https://github.com/login")

## License

MIT 