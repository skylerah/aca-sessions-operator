from playwright.sync_api import sync_playwright
import base64
import time
import os
import json

class RemotePlaywright:
    def __init__(self):
        try:
            print("Starting Playwright...")
            self.playwright = sync_playwright().start()
            print("Launching browser...")
            self.browser = self.playwright.chromium.launch(headless=False)
            print("Creating browser context...")
            self.context = self.browser.new_context()
            print("Opening new page...")
            self.page = self.context.new_page()
            print("Browser setup complete")
            
            self.screenshot_dir = "screenshots"
            
            # Create screenshot directory if it doesn't exist
            if not os.path.exists(self.screenshot_dir):
                os.makedirs(self.screenshot_dir)
                print(f"Created screenshot directory: {self.screenshot_dir}")
            
            # Verify page methods are callable
            if not callable(getattr(self.page, "goto", None)):
                print("Warning: page.goto is not callable")
            if not callable(getattr(self.page, "screenshot", None)):
                print("Warning: page.screenshot is not callable")
        except Exception as e:
            print(f"Error initializing Playwright: {e}")
            raise
    
    def _get_page_info(self):
        """Get current page dimensions and viewport information"""
        try:
            # In Playwright, viewport_size is a property, not a method
            try:
                # Try accessing it as a property first
                viewport = self.page.viewport_size
                if viewport is None:
                    # Fall back to default if property is None
                    viewport = {"width": 1280, "height": 720}
                    print("Warning: page.viewport_size is None")
            except Exception:
                # If accessing as property fails, try as a method (older versions)
                if callable(getattr(self.page, "viewport_size", None)):
                    viewport = self.page.viewport_size()
                else:
                    viewport = {"width": 1280, "height": 720}
                    print("Warning: Could not access viewport_size")
            
            # Check if evaluate is a callable function
            if callable(getattr(self.page, "evaluate", None)):
                try:
                    window_size = self.page.evaluate("""() => ({
                        width: window.innerWidth,
                        height: window.innerHeight,
                        scrollX: window.scrollX,
                        scrollY: window.scrollY,
                        devicePixelRatio: window.devicePixelRatio
                    })""")
                except Exception as eval_error:
                    print(f"Warning: Failed to evaluate window size: {eval_error}")
                    window_size = {
                        "width": 1280,
                        "height": 720,
                        "scrollX": 0,
                        "scrollY": 0,
                        "devicePixelRatio": 1
                    }
            else:
                window_size = {
                    "width": 1280,
                    "height": 720,
                    "scrollX": 0,
                    "scrollY": 0,
                    "devicePixelRatio": 1
                }
                print("Warning: page.evaluate is not callable")
            
            return {
                "viewport": viewport,
                "window": window_size,
                "timestamp": int(time.time())
            }
        except Exception as e:
            print(f"Warning: Failed to get page info: {e}")
            # Return default values
            return {
                "viewport": {"width": 1280, "height": 720},
                "window": {
                    "width": 1280,
                    "height": 720,
                    "scrollX": 0,
                    "scrollY": 0,
                    "devicePixelRatio": 1
                },
                "timestamp": int(time.time())
            }
    
    def browse_to(self, url):
        """Navigate to a website"""
        try:
            print(f"Navigating to URL: {url}")
            
            if not callable(getattr(self.page, "goto", None)):
                print("Error: page.goto is not callable")
                # Try to recreate the page if needed
                try:
                    print("Attempting to recreate page...")
                    self.page = self.context.new_page()
                except Exception as e:
                    print(f"Failed to recreate page: {e}")
            
            self.page.goto(url)
            print(f"Successfully navigated to {url}")
            
            screenshot_path = self.take_screenshot()
            return screenshot_path
        except Exception as e:
            print(f"Error navigating to {url}: {e}")
            # Still try to take a screenshot to see current state
            return self.take_screenshot()
    
    def _extract_dom_information(self):
        """Extract important DOM elements and their properties"""
        try:
            # Extract interactive elements and their properties
            dom_data = self.page.evaluate("""() => {
                function getElementInfo(element, depth = 0, maxDepth = 2) {
                    if (!element || depth > maxDepth) return null;
                    
                    // Get element position
                    const rect = element.getBoundingClientRect();
                    
                    // Basic element info
                    const info = {
                        tagName: element.tagName?.toLowerCase(),
                        id: element.id,
                        className: element.className,
                        type: element.type,
                        name: element.name,
                        value: element.value,
                        placeholder: element.placeholder,
                        href: element.href,
                        src: element.src,
                        alt: element.alt,
                        title: element.title,
                        ariaLabel: element.getAttribute('aria-label'),
                        text: element.innerText?.trim(),
                        isVisible: (
                            rect.width > 0 && 
                            rect.height > 0 && 
                            window.getComputedStyle(element).display !== 'none' && 
                            window.getComputedStyle(element).visibility !== 'hidden'
                        ),
                        position: {
                            x: rect.left + rect.width / 2,
                            y: rect.top + rect.height / 2,
                            width: rect.width,
                            height: rect.height,
                            top: rect.top,
                            left: rect.left,
                            bottom: rect.bottom,
                            right: rect.right
                        }
                    };
                    
                    return info;
                }
                
                // Get interactive elements
                const interactiveElements = [];
                const selectors = [
                    'a', 'button', 'input', 'textarea', 'select', 'option',
                    '[role="button"]', '[role="link"]', '[role="checkbox"]', '[role="radio"]',
                    '[role="tab"]', '[role="menuitem"]', '[role="combobox"]', '[role="textbox"]',
                    '[tabindex]:not([tabindex="-1"])', '[onclick]', '[onkeydown]', '[onkeyup]',
                    'label', 'form', 'nav', 'header', 'footer'
                ];
                
                document.querySelectorAll(selectors.join(', ')).forEach(element => {
                    const info = getElementInfo(element);
                    if (info && info.isVisible) {
                        interactiveElements.push(info);
                    }
                });
                
                // Get form elements specifically
                const forms = [];
                document.querySelectorAll('form').forEach(form => {
                    const formElements = [];
                    form.querySelectorAll('input, button, textarea, select').forEach(el => {
                        const info = getElementInfo(el);
                        if (info) formElements.push(info);
                    });
                    
                    forms.push({
                        id: form.id,
                        name: form.name,
                        action: form.action,
                        method: form.method,
                        elements: formElements
                    });
                });
                
                // Get current page title, URL and visible text
                return {
                    title: document.title,
                    url: window.location.href,
                    interactiveElements: interactiveElements,
                    forms: forms,
                    visibleText: document.body.innerText.substring(0, 5000) // Limit text size
                };
            }""")
            
            return dom_data
        except Exception as e:
            print(f"Warning: Failed to extract DOM information: {e}")
            return {
                "title": "Unknown",
                "url": "Unknown",
                "interactiveElements": [],
                "forms": [],
                "visibleText": ""
            }
    
    def take_screenshot(self):
        """Take a screenshot and return the path"""
        try:
            timestamp = int(time.time())
            screenshot_path = f"{self.screenshot_dir}/screenshot_{timestamp}.png"
            
            if not callable(getattr(self.page, "screenshot", None)):
                print("Error: page.screenshot is not callable")
                print("Cannot take screenshot, returning placeholder path")
                return screenshot_path
            
            print(f"Taking screenshot: {screenshot_path}")
            self.page.screenshot(path=screenshot_path)
            print("Screenshot taken successfully")
            
            # Extract DOM information
            dom_data = self._extract_dom_information()
            
            # Create a metadata file with the same name
            metadata_path = f"{self.screenshot_dir}/screenshot_{timestamp}.json"
            page_info = self._get_page_info()
            
            # Combine page info with DOM data
            metadata = {
                "page_info": page_info,
                "dom_data": dom_data,
                "timestamp": timestamp
            }
            
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            return screenshot_path
        except Exception as e:
            print(f"Error taking screenshot: {e}")
            # Return a path anyway so the workflow can continue
            return f"{self.screenshot_dir}/error_screenshot_{int(time.time())}.png"
        
    def click(self, x, y, button="left"):
        """Click at coordinates"""
        self.page.mouse.click(x, y, button=button)
        return self.take_screenshot()
    
    def double_click(self, x, y):
        """Double click at coordinates"""
        self.page.mouse.dblclick(x, y)
        return self.take_screenshot()
    
    def scroll(self, x=None, y=None, scroll_x=0, scroll_y=0):
        """Scroll at coordinates or current mouse position"""
        # If coordinates are provided, move to them first
        if x is not None and y is not None:
            self.page.mouse.move(x, y)
        
        # Perform the scroll
        self.page.mouse.wheel(delta_x=scroll_x, delta_y=scroll_y)
        return self.take_screenshot()
    
    def type(self, text):
        """Type text"""
        self.page.keyboard.type(text)
        return self.take_screenshot()
    
    def wait(self, ms=1000):
        """Wait for specified milliseconds"""
        self.page.wait_for_timeout(ms)
        return self.take_screenshot()
    
    def move(self, x, y):
        """Move to coordinates"""
        self.page.mouse.move(x, y)
        return self.take_screenshot()
    
    def keypress(self, keys):
        """Press specified keys"""
        for key in keys:
            self.page.keyboard.press(key)
        return self.take_screenshot()
    
    def drag(self, path):
        """Drag along a path of coordinates"""
        start = path[0]
        self.page.mouse.move(start[0], start[1])
        self.page.mouse.down()
        
        for point in path[1:]:
            self.page.mouse.move(point[0], point[1])
        
        self.page.mouse.up()
        return self.take_screenshot()
    
    def close(self):
        """Close browser and playwright"""
        self.context.close()
        self.browser.close()
        self.playwright.stop() 