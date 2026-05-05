"""
LangChain tools for API integration in RAG
Allows the agent to use APIs when needed
"""

from langchain.tools import Tool
from api_integrations import APIManager


def create_api_tools():
    """Create LangChain tools for API integration"""
    
    api_manager = APIManager()
    
    # Tool 1: Get Employee Info
    def get_employee_tool(username: str) -> str:
        result = api_manager.fetch_employee_data(username)
        if result["status"] == "success":
            emp = result["data"]
            return f"""
            Employee: {emp['name']}
            Role: {emp['role']}
            Department: {emp['department']}
            PTO Balance: {emp['pto_balance']} days
            Email: {emp['email']}
            """
        return result["message"]
    
    # Tool 2: Create Support Ticket
    def create_ticket_tool(title: str, description: str, priority: str, reporter: str) -> str:
        result = api_manager.create_ticket(title, description, priority, reporter)
        if result["status"] == "success":
            return f"Ticket created: {result['ticket_id']}\n{result['message']}"
        return result["message"]
    
    # Tool 3: List Tickets
    def list_tickets_tool(username: str) -> str:
        result = api_manager.list_tickets(username)
        if result["status"] == "success" and result["count"] > 0:
            tickets_str = "\n".join([f"- {t['ticket_id']}: {t['title']} ({t['priority']})" for t in result["tickets"]])
            return f"Tickets for {username}:\n{tickets_str}"
        return f"No tickets found for {username}"
    
    # Tool 4: Send Notification
    def send_notification_tool(channel: str, message: str, user: str) -> str:
        result = api_manager.send_notification(channel, message, user)
        return result["message"]
    
    # Create Tool objects
    tools = [
        Tool(
            name="get_employee_info",
            func=get_employee_tool,
            description="Get employee information from HR system including PTO balance, role, and department"
        ),
        Tool(
            name="create_support_ticket",
            func=create_ticket_tool,
            description="Create a support ticket in the ticketing system"
        ),
        Tool(
            name="list_user_tickets",
            func=list_tickets_tool,
            description="List all support tickets created by a user"
        ),
        Tool(
            name="send_notification",
            func=send_notification_tool,
            description="Send a notification to Slack, Teams, or Email"
        )
    ]
    
    return tools, api_manager
