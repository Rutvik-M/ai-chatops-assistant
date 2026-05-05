"""
API Integrations for ChatOps Assistant
Supports HR System, Ticketing System, and Notifications
"""

import json
from datetime import datetime, timedelta, UTC
from typing import Dict, Any, Optional, List
import uuid


class APIManager:
    """Central manager for all API integrations"""
    
    def __init__(self):
        self.hr_api = HRSystemIntegration()
        self.ticket_api = TicketingSystemIntegration()
        self.notify_api = NotificationIntegration()
        self.api_calls_log = []
    
    def fetch_employee_data(self, username: str) -> Dict[str, Any]:
        """Get employee info from HR system"""
        result = self.hr_api.get_employee(username)
        self._log_api_call("HR_API", "fetch_employee", result["status"])
        return result
    
    def create_ticket(self, title: str, description: str, priority: str, reporter: str) -> Dict[str, Any]:
        """Create ticket in ticketing system"""
        result = self.ticket_api.create(title, description, priority, reporter)
        self._log_api_call("TICKET_API", "create_ticket", result["status"])
        return result
    
    def list_tickets(self, username: str) -> Dict[str, Any]:
        """Get tickets for user"""
        result = self.ticket_api.list_by_reporter(username)
        self._log_api_call("TICKET_API", "list_tickets", result["status"])
        return result
    
    def get_ticket_stats(self) -> Dict[str, Any]:
        """Get ticket statistics for dashboard"""
        result = self.ticket_api.get_ticket_stats()
        self._log_api_call("TICKET_API", "get_stats", result["status"])
        return result
    
    def send_notification(self, channel: str, message: str, user: str) -> Dict[str, Any]:
        """Send notification to Slack/Teams"""
        result = self.notify_api.send(channel, message, user)
        self._log_api_call("NOTIFY_API", "send_notification", result["status"])
        return result
    
    def _log_api_call(self, service: str, method: str, status: str):
        """Log API calls for analytics"""
        self.api_calls_log.append({
            "timestamp": datetime.now().isoformat(),
            "service": service,
            "method": method,
            "status": status
        })
    
    def get_api_stats(self) -> Dict[str, Any]:
        """Get API usage statistics"""
        total_calls = len(self.api_calls_log)
        successful = sum(1 for call in self.api_calls_log if call["status"] == "success")
        failed = total_calls - successful
        
        return {
            "total_calls": total_calls,
            "successful": successful,
            "failed": failed,
            "success_rate": (successful / total_calls * 100) if total_calls > 0 else 0,
            "recent_calls": self.api_calls_log[-10:]  # Last 10 calls
        }


class HRSystemIntegration:
    """Mock HR System API (ADP/BambooHR/Workday)"""
    
    def __init__(self):
        # Mock employee database
        self.employees = {
            "admin": {
                "id": "EMP001",
                "name": "Admin User",
                "email": "admin@company.com",
                "role": "Engineering Manager",
                "department": "Engineering",
                "pto_balance": 15,
                "sick_days": 5,
                "work_anniversary": "2020-01-15",
                "manager": "None"
            },
            "finance": {
                "id": "EMP002",
                "name": "Finance Manager",
                "email": "finance@company.com",
                "role": "Finance Manager",
                "department": "Finance",
                "pto_balance": 10,
                "sick_days": 3,
                "work_anniversary": "2019-06-10",
                "manager": "CFO"
            },
            "hr": {
                "id": "EMP003",
                "name": "HR Specialist",
                "email": "hr@company.com",
                "role": "HR Specialist",
                "department": "Human Resources",
                "pto_balance": 12,
                "sick_days": 4,
                "work_anniversary": "2021-03-01",
                "manager": "VP HR"
            },
            "it_support": {
                "id": "EMP004",
                "name": "IT Support",
                "email": "it@company.com",
                "role": "IT Support Engineer",
                "department": "IT",
                "pto_balance": 14,
                "sick_days": 2,
                "work_anniversary": "2018-09-15",
                "manager": "IT Manager"
            },
            "engineering": {
                "id": "EMP005",
                "name": "Software Engineer",
                "email": "engineer@company.com",
                "role": "Senior Engineer",
                "department": "Engineering",
                "pto_balance": 16,
                "sick_days": 5,
                "work_anniversary": "2017-05-20",
                "manager": "Engineering Lead"
            },
            "general": {
                "id": "EMP006",
                "name": "General User",
                "email": "general@company.com",
                "role": "Employee",
                "department": "General",
                "pto_balance": 20,
                "sick_days": 10,
                "work_anniversary": "2022-01-01",
                "manager": "Department Head"
            }
        }
    
    def get_employee(self, username: str) -> Dict[str, Any]:
        """Fetch employee data"""
        try:
            if username in self.employees:
                emp = self.employees[username].copy()
                return {
                    "status": "success",
                    "data": emp,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "error",
                    "message": f"Employee {username} not found in HR system",
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            return {"status": "error", "message": f"HR API Error: {str(e)}"}
    
    def get_team(self, department: str) -> Dict[str, Any]:
        """Get all employees in a department"""
        try:
            team = [emp for emp in self.employees.values() if emp["department"] == department]
            return {
                "status": "success",
                "department": department,
                "count": len(team),
                "employees": team
            }
        except Exception as e:
            return {"status": "error", "message": f"HR API Error: {str(e)}"}
    
    def update_pto(self, username: str, days_used: int) -> Dict[str, Any]:
        """Update PTO balance"""
        try:
            if username in self.employees:
                old_balance = self.employees[username]["pto_balance"]
                new_balance = max(0, old_balance - days_used)
                self.employees[username]["pto_balance"] = new_balance
                
                return {
                    "status": "success",
                    "message": f"PTO updated for {username}",
                    "old_balance": old_balance,
                    "new_balance": new_balance,
                    "days_used": days_used
                }
            return {"status": "error", "message": "Employee not found"}
        except Exception as e:
            return {"status": "error", "message": f"HR API Error: {str(e)}"}


class TicketingSystemIntegration:
    """Mock Ticketing System API (JIRA/ServiceNow) with Support Team Features"""
    
    def __init__(self):
        # Store tickets by user for better organization
        self.tickets = {}  # {username: [tickets]}
        self.ticket_counter = 1000
        self.api_calls = []
    
    def create(self, title: str, description: str, priority: str, reporter: str) -> Dict[str, Any]:
        """Create a new ticket"""
        try:
            if priority not in ["low", "medium", "high", "critical"]:
                priority = "medium"
            
            ticket_id = f"CHAT-{self.ticket_counter}"
            self.ticket_counter += 1
            
            ticket = {
                "ticket_id": ticket_id,
                "title": title,
                "description": description,
                "priority": priority,
                "status": "open",
                "reporter": reporter,
                "created_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat(),
                "assignee": None,
                "assigned_by": None,
                "assigned_at": None,
                "updated_by": None,
                "comments": []
            }
            
            # Add ticket to user's list
            if reporter not in self.tickets:
                self.tickets[reporter] = []
            self.tickets[reporter].append(ticket)
            
            self._log_api_call("create_ticket", "success")
            
            return {
                "status": "success",
                "message": f"Ticket {ticket_id} created successfully",
                "ticket_id": ticket_id,
                "ticket": ticket
            }
        except Exception as e:
            self._log_api_call("create_ticket", "failed")
            return {"status": "error", "message": f"Ticket API Error: {str(e)}"}
    
    def get_ticket(self, ticket_id: str) -> Dict[str, Any]:
        """Get ticket details"""
        try:
            for user_tickets in self.tickets.values():
                for ticket in user_tickets:
                    if ticket["ticket_id"] == ticket_id:
                        self._log_api_call("get_ticket", "success")
                        return {"status": "success", "ticket": ticket}
            
            self._log_api_call("get_ticket", "failed")
            return {"status": "error", "message": f"Ticket {ticket_id} not found"}
        except Exception as e:
            self._log_api_call("get_ticket", "failed")
            return {"status": "error", "message": f"Ticket API Error: {str(e)}"}
    
    def list_by_reporter(self, username: str) -> Dict[str, Any]:
        """List tickets created by user"""
        try:
            user_tickets = self.tickets.get(username, [])
            self._log_api_call("list_by_reporter", "success")
            return {
                "status": "success",
                "count": len(user_tickets),
                "tickets": user_tickets
            }
        except Exception as e:
            self._log_api_call("list_by_reporter", "failed")
            return {"status": "error", "message": f"Ticket API Error: {str(e)}"}
    
    def list_all_tickets(self) -> Dict[str, Any]:
        """List all tickets from all users (for admin/support team)"""
        try:
            all_tickets = []
            for user, tickets in self.tickets.items():
                for ticket in tickets:
                    # Ensure reporter field exists
                    if "reporter" not in ticket:
                        ticket["reporter"] = user
                    all_tickets.append(ticket)
            
            # Sort by created date (newest first)
            all_tickets.sort(key=lambda x: x["created_at"], reverse=True)
            
            self._log_api_call("list_all_tickets", "success")
            return {
                "status": "success",
                "count": len(all_tickets),
                "tickets": all_tickets
            }
        except Exception as e:
            self._log_api_call("list_all_tickets", "failed")
            return {"status": "error", "message": f"Ticket API Error: {str(e)}"}
    
    def update_ticket_status(self, ticket_id: str, new_status: str, updated_by: str) -> Dict[str, Any]:
        """Update ticket status (for support team)"""
        try:
            valid_statuses = ["open", "in_progress", "resolved", "closed"]
            
            if new_status not in valid_statuses:
                return {
                    "status": "error",
                    "message": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
                }
            
            # Find and update ticket
            for user_tickets in self.tickets.values():
                for ticket in user_tickets:
                    if ticket["ticket_id"] == ticket_id:
                        old_status = ticket["status"]
                        ticket["status"] = new_status
                        ticket["updated_at"] = datetime.now(UTC).isoformat()
                        ticket["updated_by"] = updated_by
                        
                        self._log_api_call("update_ticket_status", "success")
                        return {
                            "status": "success",
                            "message": f"Status updated: {old_status} → {new_status}",
                            "ticket": ticket
                        }
            
            self._log_api_call("update_ticket_status", "failed")
            return {"status": "error", "message": "Ticket not found"}
        except Exception as e:
            self._log_api_call("update_ticket_status", "failed")
            return {"status": "error", "message": f"Ticket API Error: {str(e)}"}
    
    def assign_ticket(self, ticket_id: str, assignee: str, assigned_by: str) -> Dict[str, Any]:
        """Assign ticket to support team member"""
        try:
            # Find and assign ticket
            for user_tickets in self.tickets.values():
                for ticket in user_tickets:
                    if ticket["ticket_id"] == ticket_id:
                        ticket["assignee"] = assignee
                        ticket["assigned_by"] = assigned_by
                        ticket["assigned_at"] = datetime.now(UTC).isoformat()
                        ticket["updated_at"] = datetime.now(UTC).isoformat()
                        
                        # Auto-update status to in_progress if still open
                        if ticket["status"] == "open":
                            ticket["status"] = "in_progress"
                            ticket["updated_by"] = assigned_by
                        
                        self._log_api_call("assign_ticket", "success")
                        return {
                            "status": "success",
                            "message": f"Ticket assigned to {assignee}",
                            "ticket": ticket
                        }
            
            self._log_api_call("assign_ticket", "failed")
            return {"status": "error", "message": "Ticket not found"}
        except Exception as e:
            self._log_api_call("assign_ticket", "failed")
            return {"status": "error", "message": f"Ticket API Error: {str(e)}"}
    
    def get_ticket_stats(self) -> Dict[str, Any]:
        """Get ticket statistics for dashboard"""
        try:
            all_tickets = []
            for tickets in self.tickets.values():
                all_tickets.extend(tickets)
            
            stats = {
                "total": len(all_tickets),
                "open": sum(1 for t in all_tickets if t["status"] == "open"),
                "in_progress": sum(1 for t in all_tickets if t["status"] == "in_progress"),
                "resolved": sum(1 for t in all_tickets if t["status"] == "resolved"),
                "closed": sum(1 for t in all_tickets if t["status"] == "closed"),
                "by_priority": {
                    "critical": sum(1 for t in all_tickets if t["priority"] == "critical"),
                    "high": sum(1 for t in all_tickets if t["priority"] == "high"),
                    "medium": sum(1 for t in all_tickets if t["priority"] == "medium"),
                    "low": sum(1 for t in all_tickets if t["priority"] == "low"),
                }
            }
            
            self._log_api_call("get_ticket_stats", "success")
            return {
                "status": "success",
                "stats": stats
            }
        except Exception as e:
            self._log_api_call("get_ticket_stats", "failed")
            return {"status": "error", "message": f"Ticket API Error: {str(e)}"}
    
    def add_comment(self, ticket_id: str, comment: str, user: str) -> Dict[str, Any]:
        """Add comment to ticket"""
        try:
            for user_tickets in self.tickets.values():
                for ticket in user_tickets:
                    if ticket["ticket_id"] == ticket_id:
                        ticket["comments"].append({
                            "user": user,
                            "text": comment,
                            "timestamp": datetime.now(UTC).isoformat()
                        })
                        ticket["updated_at"] = datetime.now(UTC).isoformat()
                        
                        self._log_api_call("add_comment", "success")
                        return {
                            "status": "success",
                            "message": f"Comment added to {ticket_id}"
                        }
            
            self._log_api_call("add_comment", "failed")
            return {"status": "error", "message": f"Ticket {ticket_id} not found"}
        except Exception as e:
            self._log_api_call("add_comment", "failed")
            return {"status": "error", "message": f"Ticket API Error: {str(e)}"}
    
    def _log_api_call(self, method: str, status: str):
        """Log API calls for tracking"""
        self.api_calls.append({
            "timestamp": datetime.now().isoformat(),
            "method": method,
            "status": status
        })


class NotificationIntegration:
    """Mock Notification API (Slack/Microsoft Teams/Email)"""
    
    def __init__(self):
        self.notifications = []
    
    def send(self, channel: str, message: str, user: str) -> Dict[str, Any]:
        """Send notification to Slack/Teams/Email"""
        try:
            notification = {
                "id": str(uuid.uuid4())[:8],
                "timestamp": datetime.now().isoformat(),
                "channel": channel,
                "message": message,
                "sent_by": user,
                "status": "sent"
            }
            self.notifications.append(notification)
            
            return {
                "status": "success",
                "message": f"Notification sent to {channel}",
                "notification_id": notification["id"]
            }
        except Exception as e:
            return {"status": "error", "message": f"Notification API Error: {str(e)}"}
    
    def get_history(self, channel: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
        """Get notification history"""
        try:
            if channel:
                history = [n for n in self.notifications if n["channel"] == channel]
            else:
                history = self.notifications
            
            return {
                "status": "success",
                "count": len(history),
                "notifications": history[-limit:]
            }
        except Exception as e:
            return {"status": "error", "message": f"Notification API Error: {str(e)}"}
