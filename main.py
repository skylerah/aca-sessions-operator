#!/usr/bin/env python3
import os
import argparse
import traceback
from operator_agent import OperatorAgent

def main():
    parser = argparse.ArgumentParser(description="Browser Operator Agent")
    parser.add_argument("--goal", type=str, required=True, help="Goal for the operator agent to accomplish")
    parser.add_argument("--max-steps", type=int, default=20, help="Maximum number of steps to take (default: 20)")
    parser.add_argument("--api-key", type=str, help="OpenAI API key (or set OPENAI_API_KEY environment variable)")
    parser.add_argument("--start-url", type=str, help="Optional starting URL to navigate to before beginning the task")
    
    args = parser.parse_args()
    
    try:
        print("Initializing operator agent...")
        agent = OperatorAgent(api_key=args.api_key)
        
        print(f"Starting run with goal: {args.goal}")
        result = agent.run(goal=args.goal, max_steps=args.max_steps, start_url=args.start_url)
        
        print("\n--- Task Result ---")
        print(f"Goal: {result['goal']}")
        print(f"Steps Taken: {result['steps_taken']}")
        print(f"Goal Completed: {result['goal_completed']}")
        print(f"Final Screenshot: {result['final_screenshot']}")
        
    except Exception as e:
        print(f"Error: {e}")
        print("Detailed traceback:")
        traceback.print_exc()
    finally:
        if 'agent' in locals():
            try:
                agent.close()
            except Exception as close_error:
                print(f"Error closing agent: {close_error}")

if __name__ == "__main__":
    main() 