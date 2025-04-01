import os
import json
import time
import base64
from openai import OpenAI
from remote_playwright import RemotePlaywright

class OperatorAgent:
    def __init__(self, api_key=None):
        # Initialize API key with proper error checking
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable or pass it as a parameter.")
        
        # Initialize OpenAI client
        try:
            print("Initializing OpenAI client...")
            self.client = OpenAI(api_key=self.api_key)
        except Exception as e:
            raise Exception(f"Failed to initialize OpenAI client: {e}")
        
        # Initialize browser
        try:
            print("Initializing Playwright browser...")
            self.browser = RemotePlaywright()
            print("Browser initialization successful")
        except Exception as e:
            raise Exception(f"Failed to initialize Playwright browser: {e}")
        
        self.action_history = []
        
    def _encode_image(self, image_path):
        """Encode image to base64 for sending to OpenAI"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def analyze_screenshot(self, screenshot_path, goal, last_action=None):
        """Use GPT-4o to analyze the screenshot and recommend the next action"""
        base64_image = self._encode_image(screenshot_path)
        
        # Load the metadata file
        metadata_path = screenshot_path.replace('.png', '.json')
        page_info = {}
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                page_info = json.load(f)
        
        messages = [
            {"role": "system", "content": """You are a browser automation agent. You are given a screenshot of a webpage and a goal. 
             Your task is to identify what action to take next to accomplish the goal.
             
             IMPORTANT WEB INTERACTION PATTERNS:
             1. Before typing in an input field, you MUST first click on it to focus it
             2. Common sequences:
                - For forms: click input field → type text → click submit button
                - For captchas: click on captcha input → type captcha text → click verify button
                - For search: click search box → type query → click search button or press Enter
             3. Never use the type action without first clicking on the target input field
             4. After typing, you usually need to click a button to submit the form or press Enter
             
             SCROLLING AND PAGE EXPLORATION:
             1. If you can't find an element you're looking for (like a button, link, or form), you MUST scroll to explore more of the page
             2. E-commerce pages often have "Add to Cart" buttons below the initial viewport - scroll down to find them
             3. Navigation menus and search bars may be at the top - scroll up if you don't see them
             4. When in doubt about where an element might be, use these scrolling patterns:
                - First scroll down gradually to explore the content (scroll_y: 300-500)
                - If you reach the bottom and haven't found what you need, scroll back up
                - Always check the page header and footer as they often contain important navigation
             5. After scrolling, take time to fully analyze the new content that has appeared
             
             For each action, you must provide detailed information about the target element:
             - Element type (button, link, input field, etc.)
             - Visual characteristics (color, size, text content, etc.)
             - Location on the page (top, bottom, left, right, etc.)
             - Surrounding context (what's next to it, above it, below it)
             
             You must return a JSON object with the following structure:
             {
                "reasoning": "Your step-by-step reasoning about what you observe and what action to take",
                "action": "The action to take (browse_to, click, double_click, scroll, type, wait, move, keypress, drag)",
                "params": {
                    // For browse_to:
                    "url": "https://example.com",
                    
                    // For click, double_click, scroll, move:
                    "x": 100,
                    "y": 200,
                    
                    // For click only (optional):
                    "button": "left", // or "right", "middle"
                    
                    // For scroll only:
                    "scroll_x": 0,
                    "scroll_y": -100,
                    
                    // For type:
                    "text": "text to type",
                    
                    // For wait:
                    "ms": 1000,
                    
                    // For keypress:
                    "keys": ["CTRL", "C"],
                    
                    // For drag:
                    "path": [[x1, y1], [x2, y2], ...]
                },
                "element_details": {
                    "type": "Type of element (button, link, input, etc.)",
                    "visual_description": "Detailed visual description of the element",
                    "location": "Where the element is located on the page",
                    "context": "What surrounds the element",
                    "confidence": 0.95, // Confidence score between 0 and 1
                    "alternative_coordinates": [ // Alternative coordinates if the primary ones don't work
                        {"x": 105, "y": 205},
                        {"x": 95, "y": 195}
                    ]
                },
                "goal_completed": boolean indicating if the goal has been completed
             }
             
             When you recommend coordinates, use the format [x, y] where x and y are integers.
             Be precise about the elements you are targeting - look for buttons, links, input fields, etc.
             Whenever you recommend clicking or interacting with an element, provide the precise (x,y) coordinates.
             
             If this is your first action and you need to navigate to a website, use the browse_to action with an appropriate URL.
             
             For click actions, provide alternative coordinates slightly offset from the main coordinates.
             This helps handle cases where the element might be slightly offset from where we expect it to be.
             
             IMPORTANT: When providing coordinates, take into account:
             1. The viewport size and window dimensions
             2. The current scroll position
             3. The device pixel ratio
             
             The coordinates should be relative to the current viewport, taking into account any scrolling.
             """},
            {"role": "user", "content": [
                {"type": "text", "text": f"""Goal: {goal}

Page Information:
Viewport Size: {page_info.get('viewport', {}).get('width', 'unknown')}x{page_info.get('viewport', {}).get('height', 'unknown')}
Window Size: {page_info.get('window', {}).get('width', 'unknown')}x{page_info.get('window', {}).get('height', 'unknown')}
Scroll Position: ({page_info.get('window', {}).get('scrollX', 'unknown')}, {page_info.get('window', {}).get('scrollY', 'unknown')})
Device Pixel Ratio: {page_info.get('window', {}).get('devicePixelRatio', 'unknown')}

Analyze this screenshot and recommend the next action to take."""},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
            ]}
        ]
        
        # Add last action to context if available
        if last_action:
            messages[1]["content"][0]["text"] += f"\n\nLast action: {json.dumps(last_action)}"
        else:
            messages[1]["content"][0]["text"] += "\n\nThis is the first action to take. If you need to navigate to a website, use the browse_to action."
        
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
    
    def _extract_param(self, params, param_names, default=None):
        """Helper method to extract parameters from various possible keys or indices"""
        if not isinstance(params, dict):
            return default
            
        for name in param_names:
            if name in params and params[name] is not None:
                return params[name]
        
        # Check for param1, param2, etc.
        for i in range(1, 10):
            param_key = f"param{i}"
            if param_key in params and params[param_key] is not None:
                return params[param_key]
        
        return default
    
    def execute_action(self, action_data):
        """Execute the action recommended by the AI"""
        if not isinstance(action_data, dict):
            raise ValueError(f"action_data must be a dictionary, got {type(action_data)}")
            
        action = action_data.get("action")
        if not action:
            raise ValueError("Action is required in action_data")
            
        params = action_data.get("params", {})
        if not isinstance(params, dict):
            # Convert to dict if it's not already
            params = {}
            
        element_details = action_data.get("element_details", {})
        
        # Debug logging
        print(f"\nDebug - Action Data:")
        print(f"Action: {action}")
        print(f"Params type: {type(params)}")
        print(f"Params: {params}")
        print(f"Element details: {element_details}")
        
        # Record action for history
        self.action_history.append(action_data)
        
        screenshot_path = None
        
        # Handle actions based on type
        if action == "browse_to":
            url = self._extract_param(params, ["url"])
            if not url:
                raise ValueError("URL is required for browse_to action")
            screenshot_path = self.browser.browse_to(url)
            
        elif action == "click" or action == "double_click":
            max_attempts = 3
            attempt = 0
            
            while attempt < max_attempts:
                try:
                    if attempt == 0:
                        # First try with primary coordinates
                        x = self._extract_param(params, ["x"])
                        y = self._extract_param(params, ["y"])
                    else:
                        # Try alternative coordinates
                        alt_coords = element_details.get("alternative_coordinates", [])
                        if attempt - 1 < len(alt_coords):
                            x = alt_coords[attempt - 1]["x"]
                            y = alt_coords[attempt - 1]["y"]
                        else:
                            break
                    
                    button = self._extract_param(params, ["button"], "left")
                    
                    if x is None or y is None:
                        raise ValueError(f"x and y coordinates are required for {action} action. Received: {params}")
                    
                    # Log attempt details
                    print(f"\nAttempt {attempt + 1}/{max_attempts}:")
                    print(f"Clicking at coordinates: ({x}, {y})")
                    print(f"Element details: {element_details.get('visual_description', 'No description available')}")
                    
                    # Execute the action
                    if action == "click":
                        screenshot_path = self.browser.click(x, y, button)
                        break
                    else:  # double_click
                        screenshot_path = self.browser.double_click(x, y)
                        break
                        
                except Exception as e:
                    print(f"Attempt {attempt + 1} failed: {e}")
                    attempt += 1
                    if attempt < max_attempts:
                        print("Trying alternative coordinates...")
                        time.sleep(0.5)  # Small delay between attempts
                    else:
                        raise Exception(f"All {max_attempts} attempts failed")
            
        elif action == "scroll":
            x = self._extract_param(params, ["x"])
            y = self._extract_param(params, ["y"])
            scroll_x = self._extract_param(params, ["scroll_x"], 0)
            scroll_y = self._extract_param(params, ["scroll_y"], 0)
            
            # x and y are optional for scroll action
            screenshot_path = self.browser.scroll(x, y, scroll_x, scroll_y)
            
        elif action == "type":
            text = self._extract_param(params, ["text"])
            
            if text is None:
                raise ValueError(f"text is required for type action. Received: {params}")
                
            screenshot_path = self.browser.type(text)
            
        elif action == "wait":
            ms = self._extract_param(params, ["ms"], 1000)
            screenshot_path = self.browser.wait(ms)
            
        elif action == "move":
            x = self._extract_param(params, ["x"])
            y = self._extract_param(params, ["y"])
            
            if x is None or y is None:
                raise ValueError(f"x and y coordinates are required for move action. Received: {params}")
                
            screenshot_path = self.browser.move(x, y)
            
        elif action == "keypress":
            keys = self._extract_param(params, ["keys"])
            
            if keys is None:
                raise ValueError(f"keys is required for keypress action. Received: {params}")
                
            screenshot_path = self.browser.keypress(keys)
            
        elif action == "drag":
            path = self._extract_param(params, ["path"])
            
            if path is None:
                raise ValueError(f"path is required for drag action. Received: {params}")
                
            screenshot_path = self.browser.drag(path)
            
        elif action == "take_screenshot":
            screenshot_path = self.browser.take_screenshot()
            
        else:
            raise ValueError(f"Unknown action: {action}")
            
        if screenshot_path is None:
            # Fallback to taking a screenshot if no path was returned
            screenshot_path = self.browser.take_screenshot()
            
        return screenshot_path
    
    def run(self, goal, max_steps=20, start_url=None):
        """Run the operator agent to accomplish a goal"""
        print(f"Starting to accomplish goal: {goal}")
        
        # Start by navigating to a URL if provided
        if start_url:
            print(f"Navigating to starting URL: {start_url}")
            screenshot_path = self.browser.browse_to(start_url)
            last_action = {
                "action": "browse_to",
                "params": {"url": start_url},
                "reasoning": "Initial navigation to starting URL"
            }
        else:
            # Start by taking a screenshot of the current state
            screenshot_path = self.browser.take_screenshot()
            last_action = None
        
        for step in range(max_steps):
            print(f"\nStep {step+1}/{max_steps}:")
            
            # Analyze screenshot and get next action
            analysis = self.analyze_screenshot(screenshot_path, goal, last_action)
            
            # Log reasoning
            print(f"Reasoning: {analysis.get('reasoning')}")
            print(f"Action: {analysis.get('action')}")
            print(f"Params: {analysis.get('params')}")
            
            # Check if goal is completed
            if analysis.get("goal_completed", False):
                print(f"\nGoal completed in {step+1} steps!")
                break
            
            try:
                # Execute the action
                screenshot_path = self.execute_action(analysis)
                last_action = analysis
            except Exception as e:
                print(f"Error executing action: {e}")
                print("Retrying with next action...")
                continue
            
            # Small delay to avoid API rate limits
            time.sleep(1)
        
        # Take a final screenshot
        final_screenshot = self.browser.take_screenshot()
        print(f"Final screenshot saved at: {final_screenshot}")
        
        return {
            "goal": goal,
            "steps_taken": step + 1,
            "action_history": self.action_history,
            "final_screenshot": final_screenshot,
            "goal_completed": analysis.get("goal_completed", False)
        }
    
    def close(self):
        """Close the browser"""
        self.browser.close() 