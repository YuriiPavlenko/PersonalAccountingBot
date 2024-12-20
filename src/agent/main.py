import logging
import pytz
import os
from datetime import datetime
from typing import TypeVar, List, Union, Dict, Any
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langchain.tools import StructuredTool
from langchain.prompts import ChatPromptTemplate
from langsmith import Client
from langchain_core.tracers import LangChainTracer
from src.schemas import ExpenseSchema
from pydantic import BaseModel

# Define state types
S = TypeVar("S", bound=Dict[str, Any])

class GetTimeToolSchema(BaseModel):
    """Schema for get_current_time tool that takes no arguments"""
    pass

class ExpenseTrackingAgent:
    def __init__(self, sheets_client):
        self.logger = logging.getLogger(__name__)
        
        self.logger.info("Initializing LangSmith...")
        self.langsmith_client = Client()
        self.tracer = LangChainTracer(project_name="expense_tracking")
        
        self.logger.info("Initializing ChatOpenAI...")
        self.llm = ChatOpenAI()
        
        self.logger.info("Setting up SheetsClient...")
        self.sheets_client = sheets_client
        
        self.logger.info("Creating tools...")
        self.tools = self._create_tools()
        
        self.logger.info("Creating workflow graph...")
        self.workflow = self._create_workflow()

    def _create_tools(self) -> List[StructuredTool]:
        """Create the agent's tools"""
        append_expense_tool = StructuredTool(
            name="append_expense_to_table",
            description="Formats an expense entry for confirmation",
            func=self._format_expense,
            args_schema=ExpenseSchema
        )
        
        get_time_tool = StructuredTool(
            name="get_current_time",
            description="Returns current time in Thailand timezone",
            func=self._get_current_time,
            args_schema=GetTimeToolSchema  # Add args_schema even though it takes no arguments
        )
        
        return [append_expense_tool, get_time_tool]

    def _create_workflow(self) -> StateGraph:
        """Create the workflow graph"""
        # Create the graph
        workflow = StateGraph(S)

        # Add nodes
        workflow.add_node("parse_expense", self._parse_expense)
        workflow.add_node("format_for_confirmation", self._format_for_confirmation)
        workflow.add_node("await_confirmation", self._await_confirmation)
        workflow.add_node("write_to_sheet", self._write_to_sheet)

        # Add edges
        workflow.add_edge("parse_expense", "format_for_confirmation")
        workflow.add_edge("format_for_confirmation", "await_confirmation")
        workflow.add_edge("await_confirmation", "write_to_sheet")
        workflow.add_edge("write_to_sheet", END)

        # Set entry point
        workflow.set_entry_point("parse_expense")

        return workflow.compile()

    async def _parse_expense(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Parse expense information from user input"""
        with self.tracer.start_span("parse_expense") as span:
            prompt = ChatPromptTemplate.from_messages([
                ("system", "Extract expense information from the user message. Return a JSON object with date, description, amount, currency, cash (boolean), and user fields."),
                ("user", "{input}")
            ])
            
            chain = prompt | self.llm
            span.log({"input": state["message"]})
            result = await chain.ainvoke({"input": state["message"]})
            span.log({"output": result})
            return {"expense_data": result}

    async def _format_for_confirmation(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Format expense for user confirmation"""
        expense_data = state["expense_data"]
        formatted = f"""
📝 Expense Details:
📅 Date: {expense_data['date']}
💰 Amount: {expense_data['amount']} {expense_data['currency']}
📄 Description: {expense_data['description']}
💳 Payment Type: {'Cash' if expense_data['cash'] else 'Card'}
👤 User: {expense_data['user']}
"""
        return {**state, "formatted_expense": formatted}

    async def _await_confirmation(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Await user confirmation"""
        # This node doesn't do anything as confirmation is handled by the bot
        return state

    async def _write_to_sheet(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Write confirmed expense to sheet"""
        await self.sheets_client.append_expense(**state["expense_data"])
        return {**state, "status": "written"}

    def _format_expense(self, **kwargs) -> Dict[str, Any]:
        """Format expense data"""
        return kwargs

    def _get_current_time(self) -> str:
        """Get current time in Thailand timezone"""
        self.logger.info("Fetching current time")
        tz = pytz.timezone('Asia/Bangkok')
        return datetime.now(tz).isoformat()

    async def process_message(self, message: str) -> Dict[str, Any]:
        """Process a new expense message"""
        self.logger.info(f"Processing message: {message}")
        try:
            result = await self.workflow.ainvoke({"message": message})
            self.logger.info(f"Workflow completed with result: {result}")
            return {
                "data": result["expense_data"],
                "summary": result["formatted_expense"]
            }
        except Exception as e:
            self.logger.error(f"Error processing message: {str(e)}")
            raise

    async def write_expense(self, expense_data: Dict[str, Any]) -> None:
        """Write a confirmed expense to the sheet"""
        self.logger.info(f"Writing expense to sheet: {expense_data}")
        try:
            await self.sheets_client.append_expense(**expense_data["data"])
            self.logger.info("Successfully wrote expense to sheet")
        except Exception as e:
            self.logger.error(f"Failed to write expense to sheet: {str(e)}")
            raise
