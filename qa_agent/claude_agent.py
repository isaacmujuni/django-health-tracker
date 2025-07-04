import asyncio
import json
from typing import List, Dict, Any, Optional
import anthropic
from django.conf import settings
from fitness.models import FitnessActivity, DietaryLog, WeightEntry, FitnessGoal
from django.contrib.auth.models import User
# TODO: Implement these tools
# from .tools.web_search import WebSearchTool
# from .tools.document_reader import DocumentReaderTool
# from .tools.health_analyzer import HealthAnalyzerTool


class ClaudeQAAgent:
    """
    Claude-powered QA Agent that leverages Claude's advanced tool calling capabilities
    
    Key Features:
    - Parallel tool execution for efficiency
    - Intelligent tool selection based on context
    - Multi-step reasoning with tool chaining
    - Error handling and adaptive retry logic
    - Real-time status updates via WebSocket
    """
    
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.tools = self._initialize_claude_tools()
        self.tool_executors = self._initialize_tool_executors()
        self.status_callback = None  # For real-time updates
    
    def set_status_callback(self, callback):
        """Set callback function for real-time status updates"""
        self.status_callback = callback
    
    def _initialize_claude_tools(self):
        """
        Define tools in Claude's function calling format
        This is the key to leveraging Claude's tool capabilities
        """
        return [
            {
                "name": "search_web",
                "description": "Search the internet for current information on health, fitness, nutrition, or medical topics",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string", 
                            "description": "Search query with relevant keywords"
                        },
                        "focus_area": {
                            "type": "string",
                            "enum": ["health", "fitness", "nutrition", "medical", "general"],
                            "description": "Focus area for more targeted results"
                        },
                        "num_results": {
                            "type": "integer", 
                            "default": 5,
                            "description": "Number of results to return"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "read_documents",
                "description": "Read and analyze documents from specified folders (PDFs, DOCX, TXT files)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "folder_path": {
                            "type": "string",
                            "description": "Path to folder containing documents"
                        },
                        "file_types": {
                            "type": "array",
                            "items": {"type": "string"},
                            "default": ["pdf", "docx", "txt"],
                            "description": "File types to process"
                        },
                        "search_terms": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional terms to search for within documents"
                        }
                    },
                    "required": ["folder_path"]
                }
            },
            {
                "name": "analyze_user_health_data",
                "description": "Query and analyze user's fitness activities, diet logs, weight entries, and goals",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "integer",
                            "description": "User ID to query data for"
                        },
                        "data_types": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": ["activities", "diet", "weight", "goals", "all"]
                            },
                            "description": "Types of health data to analyze"
                        },
                        "date_range": {
                            "type": "string",
                            "description": "Date range in format 'YYYY-MM-DD,YYYY-MM-DD' or relative like 'last_30_days'"
                        },
                        "analysis_type": {
                            "type": "string",
                            "enum": ["trends", "summary", "detailed", "patterns"],
                            "default": "summary",
                            "description": "Type of analysis to perform"
                        }
                    },
                    "required": ["user_id", "data_types"]
                }
            },
            {
                "name": "generate_health_plan",
                "description": "Generate personalized health/fitness plans based on user data and research",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "plan_type": {
                            "type": "string",
                            "enum": ["workout", "diet", "weight_loss", "muscle_gain", "general_health"],
                            "description": "Type of plan to generate"
                        },
                        "user_data": {
                            "type": "object",
                            "description": "User's health data and preferences"
                        },
                        "research_data": {
                            "type": "object",
                            "description": "Research findings to incorporate"
                        },
                        "duration": {
                            "type": "string",
                            "default": "4_weeks",
                            "description": "Plan duration"
                        }
                    },
                    "required": ["plan_type", "user_data"]
                }
            }
        ]
    
    def _initialize_tool_executors(self):
        """Initialize actual tool execution classes"""
        return {
            "search_web": self._mock_web_search,
            "read_documents": self._mock_document_reader,
            "analyze_user_health_data": self._mock_health_analyzer,
            "generate_health_plan": self._generate_health_plan
        }
    
    async def process_question(self, question: str, user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Main method that leverages Claude's intelligent tool orchestration
        
        Claude will:
        1. Analyze the question
        2. Determine which tools are needed
        3. Execute tools in parallel where possible
        4. Chain tool results for complex reasoning
        5. Synthesize a comprehensive answer
        """
        
        # Build context for Claude
        messages = [
            {
                "role": "user", 
                "content": self._build_context_prompt(question, user_context)
            }
        ]
        
        try:
            # Let Claude decide which tools to use and how
            response = await self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                messages=messages,
                tools=self.tools,
                tool_choice="auto"  # Let Claude decide when to use tools
            )
            
            # Process Claude's tool calls
            if response.stop_reason == "tool_use":
                tool_results = await self._execute_claude_tool_calls(response.content)
                
                # Continue conversation with tool results
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})
                
                # Get Claude's final analysis
                final_response = await self.client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=4000,
                    messages=messages
                )
                
                return {
                    "answer": final_response.content[0].text,
                    "tools_used": self._extract_tools_used(response.content),
                    "reasoning_steps": self._extract_reasoning_steps(response.content),
                    "confidence": self._calculate_confidence(tool_results)
                }
            else:
                # Claude answered without tools
                return {
                    "answer": response.content[0].text,
                    "tools_used": [],
                    "reasoning_steps": ["Direct answer based on training data"],
                    "confidence": 0.8
                }
                
        except Exception as e:
            return {
                "answer": f"I encountered an error processing your question: {str(e)}",
                "tools_used": [],
                "reasoning_steps": ["Error occurred"],
                "confidence": 0.0
            }
    
    async def _execute_claude_tool_calls(self, content: List[Dict]) -> str:
        """
        Execute the tools that Claude requested
        This is where Claude's parallel execution shines
        """
        tool_calls = [block for block in content if block.type == "tool_use"]
        
        if not tool_calls:
            return "No tools were called."
        
        # Execute tools in parallel (Claude's key advantage)
        tasks = []
        for tool_call in tool_calls:
            task = self._execute_single_tool(tool_call.name, tool_call.input, tool_call.id)
            tasks.append(task)
        
        # Wait for all tools to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Format results for Claude
        tool_results = []
        for i, result in enumerate(results):
            tool_call = tool_calls[i]
            if isinstance(result, Exception):
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_call.id,
                    "content": f"Error executing {tool_call.name}: {str(result)}"
                })
            else:
                tool_results.append({
                    "type": "tool_result", 
                    "tool_use_id": tool_call.id,
                    "content": json.dumps(result) if isinstance(result, dict) else str(result)
                })
        
        return json.dumps(tool_results)
    
    async def _execute_single_tool(self, tool_name: str, tool_input: Dict, tool_id: str) -> Any:
        """Execute a single tool with error handling and real-time updates"""
        try:
            # Notify tool started
            if self.status_callback:
                description = self._get_tool_description(tool_name, tool_input)
                await self.status_callback('tool_started', tool_name, description)
            
            executor = self.tool_executors.get(tool_name)
            if not executor:
                raise ValueError(f"Unknown tool: {tool_name}")
            
            # Execute the tool
            if callable(executor):
                result = await executor(**tool_input)
            else:
                result = await executor.execute(**tool_input)
            
            # Notify tool completed
            if self.status_callback:
                await self.status_callback('tool_completed', tool_name, 
                                         self._format_tool_result(tool_name, result))
            
            return result
            
        except Exception as e:
            # Notify tool error
            if self.status_callback:
                await self.status_callback('tool_error', tool_name, str(e))
            return {"error": str(e), "tool": tool_name}
    
    def _get_tool_description(self, tool_name: str, tool_input: Dict) -> str:
        """Get human-readable description of what the tool is doing"""
        descriptions = {
            'search_web': f"Searching the web for: {tool_input.get('query', 'health information')}",
            'read_documents': f"Reading documents from: {tool_input.get('folder_path', 'specified folder')}",
            'analyze_user_health_data': f"Analyzing your {', '.join(tool_input.get('data_types', ['health data']))}",
            'generate_health_plan': f"Creating a {tool_input.get('plan_type', 'health')} plan for you"
        }
        return descriptions.get(tool_name, f"Executing {tool_name}")
    
    def _format_tool_result(self, tool_name: str, result: Any) -> str:
        """Format tool result for display"""
        if isinstance(result, dict) and result.get('error'):
            return f"Error: {result['error']}"
        
        summaries = {
            'search_web': "Found relevant health information",
            'read_documents': "Analyzed documents successfully",
            'analyze_user_health_data': "Completed health data analysis",
            'generate_health_plan': "Generated personalized plan"
        }
        return summaries.get(tool_name, "Completed successfully")
    
    def _build_context_prompt(self, question: str, user_context: Dict = None) -> str:
        """Build a rich context prompt for Claude"""
        prompt = f"""You are a health and fitness question answering agent integrated into a Django health tracker application.

User Question: {question}

"""
        
        if user_context:
            prompt += f"""User Context:
- User ID: {user_context.get('user_id', 'Unknown')}
- Recent Activity Count: {user_context.get('activity_count', 0)}
- Current Goals: {user_context.get('goals', 'None set')}
- Last Weight Entry: {user_context.get('last_weight', 'No data')}

"""
        
        prompt += """Available Tools:
You have access to several powerful tools that you can use in parallel:

1. search_web - Find current health/fitness research and information
2. read_documents - Analyze documents from folders (research papers, guides, etc.)
3. analyze_user_health_data - Query the user's fitness activities, diet, weight, and goals
4. generate_health_plan - Create personalized health plans based on data and research

Instructions:
- Use multiple tools in parallel when beneficial (e.g., search web while analyzing user data)
- Chain tools logically (gather data first, then analyze and synthesize)
- Always consider both user-specific data AND current research/best practices
- Provide evidence-based recommendations with sources when possible
- If user data is relevant to the question, always analyze it
- For complex questions, break down your approach into clear reasoning steps

Please analyze this question and use the appropriate tools to provide a comprehensive, personalized answer."""
        
        return prompt
    
    def _extract_tools_used(self, content: List[Dict]) -> List[str]:
        """Extract which tools Claude used"""
        return [block.name for block in content if block.type == "tool_use"]
    
    def _extract_reasoning_steps(self, content: List[Dict]) -> List[str]:
        """Extract Claude's reasoning process"""
        text_blocks = [block.text for block in content if block.type == "text"]
        # This would need more sophisticated parsing in practice
        return text_blocks[:1] if text_blocks else ["Analysis performed"]
    
    def _calculate_confidence(self, tool_results: str) -> float:
        """Calculate confidence based on tool success"""
        try:
            results = json.loads(tool_results)
            successful_tools = sum(1 for result in results if "error" not in result.get("content", ""))
            total_tools = len(results)
            return successful_tools / total_tools if total_tools > 0 else 0.8
        except:
            return 0.7
    
    async def _generate_health_plan(self, **kwargs) -> Dict[str, Any]:
        """Generate health plan tool implementation"""
        plan_type = kwargs.get('plan_type')
        user_data = kwargs.get('user_data', {})
        research_data = kwargs.get('research_data', {})
        duration = kwargs.get('duration', '4_weeks')
        
        # This would contain sophisticated plan generation logic
        return {
            "plan_type": plan_type,
            "duration": duration,
            "generated": True,
            "recommendations": f"Generated {plan_type} plan for {duration}",
            "user_data_incorporated": bool(user_data),
            "research_based": bool(research_data)
        }


# Example usage demonstrating Claude's capabilities
class ClaudeAgentDemo:
    """
    Demo showing how Claude orchestrates tools intelligently
    """
    
    @staticmethod
    async def demo_parallel_execution():
        """
        Example: User asks "Create a workout plan based on my recent activities and current research"
        
        Claude will automatically:
        1. analyze_user_health_data(activities, last_30_days) 
        2. search_web("latest workout research 2024") [PARALLEL]
        3. read_documents(fitness_research_folder) [PARALLEL]
        4. generate_health_plan(workout, user_data + research)
        """
        agent = ClaudeQAAgent()
        
        question = "Create a workout plan based on my recent activities and current research on HIIT training"
        user_context = {
            "user_id": 1,
            "activity_count": 15,
            "goals": "Weight loss and muscle gain"
        }
        
        response = await agent.process_question(question, user_context)
        return response
    
    @staticmethod
    async def demo_intelligent_tool_selection():
        """
        Example: Claude automatically determines which tools are needed
        
        Question: "How effective is my current diet for weight loss?"
        Claude chooses: analyze_user_health_data + search_web (nutrition research)
        
        Question: "What are the latest guidelines for cardio exercise?"
        Claude chooses: search_web + read_documents (if research folder available)
        """
        agent = ClaudeQAAgent()
        
        questions = [
            "How effective is my current diet for weight loss?",
            "What are the latest guidelines for cardio exercise?",
            "Compare my progress to recommended fitness standards"
        ]
        
        results = []
        for question in questions:
            response = await agent.process_question(question, {"user_id": 1})
            results.append({
                "question": question,
                "tools_used": response["tools_used"],
                "reasoning": response["reasoning_steps"]
            })
        
        return results 