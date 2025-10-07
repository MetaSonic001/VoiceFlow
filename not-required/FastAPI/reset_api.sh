#!/bin/bash

# VoiceFlow AI API Reset Script
# This script helps you reset the API and database for fresh testing

echo "🔄 VoiceFlow AI API Reset Utility"
echo "=================================="

show_menu() {
    echo ""
    echo "Choose an option:"
    echo "1. 🗑️  Reset Database (Delete all data)"
    echo "2. 📊 Show Database Contents"
    echo "3. 🧹 Clear Session Agents (Memory cleanup)"
    echo "4. 🔍 Check Database Size"
    echo "5. 📋 List All Tables"
    echo "6. 🚀 Full Reset (Database + Sessions)"
    echo "7. ❌ Exit"
    echo ""
    read -p "Enter your choice (1-7): " choice
}

reset_database() {
    echo "🗑️ Resetting database..."
    
    # Stop the FastAPI server first (if running)
    echo "⚠️  Make sure to stop the FastAPI server before resetting!"
    read -p "Press Enter to continue or Ctrl+C to cancel..."
    
    # Remove the SQLite database file
    if [ -f "voiceflow.db" ]; then
        rm voiceflow.db
        echo "✅ Database file deleted successfully"
    else
        echo "ℹ️  Database file not found (already clean)"
    fi
    
    # Remove any uploaded files (if you're storing them locally)
    if [ -d "uploads" ]; then
        rm -rf uploads
        echo "✅ Uploads directory cleaned"
    fi
    
    echo "✅ Database reset complete. Restart the FastAPI server to create fresh tables."
}

show_database_contents() {
    echo "📊 Database Contents:"
    echo "--------------------"
    
    if [ ! -f "voiceflow.db" ]; then
        echo "❌ Database file not found. Run the API first to create it."
        return
    fi
    
    echo "Companies:"
    sqlite3 voiceflow.db "SELECT id, name, industry, bucket_id FROM companies;" 2>/dev/null || echo "No companies table"
    
    echo -e "\nUsers:"
    sqlite3 voiceflow.db "SELECT id, email, company_id, role FROM users;" 2>/dev/null || echo "No users table"
    
    echo -e "\nAgents:"
    sqlite3 voiceflow.db "SELECT id, name, role, company_id, is_active FROM agents;" 2>/dev/null || echo "No agents table"
    
    echo -e "\nDocuments:"
    sqlite3 voiceflow.db "SELECT id, filename, company_id, LENGTH(content) as content_length FROM documents;" 2>/dev/null || echo "No documents table"
    
    echo -e "\nDocument Chunks:"
    sqlite3 voiceflow.db "SELECT COUNT(*) as chunk_count, bucket_id FROM document_chunks GROUP BY bucket_id;" 2>/dev/null || echo "No chunks table"
    
    echo -e "\nSessions:"
    sqlite3 voiceflow.db "SELECT id, user_id, agent_instance_id, is_active FROM sessions;" 2>/dev/null || echo "No sessions table"
    
    echo -e "\nConversations:"
    sqlite3 voiceflow.db "SELECT COUNT(*) as conversation_count, message_type FROM conversations GROUP BY message_type;" 2>/dev/null || echo "No conversations table"
}

clear_session_agents() {
    echo "🧹 Clearing session agents from memory..."
    echo "This requires restarting the FastAPI server to clear in-memory session agents."
    echo "The session_agents and company_retrievers dictionaries will be reset."
    echo "✅ Memory cleanup instructions provided. Please restart the API server."
}

check_database_size() {
    echo "🔍 Database Information:"
    echo "-----------------------"
    
    if [ -f "voiceflow.db" ]; then
        size=$(du -h voiceflow.db | cut -f1)
        echo "Database size: $size"
        
        echo -e "\nTable row counts:"
        sqlite3 voiceflow.db "SELECT 'companies', COUNT(*) FROM companies UNION ALL 
                             SELECT 'users', COUNT(*) FROM users UNION ALL 
                             SELECT 'agents', COUNT(*) FROM agents UNION ALL 
                             SELECT 'documents', COUNT(*) FROM documents UNION ALL 
                             SELECT 'document_chunks', COUNT(*) FROM document_chunks UNION ALL 
                             SELECT 'sessions', COUNT(*) FROM sessions UNION ALL 
                             SELECT 'conversations', COUNT(*) FROM conversations UNION ALL
                             SELECT 'call_logs', COUNT(*) FROM call_logs;" 2>/dev/null
    else
        echo "❌ Database file not found"
    fi
}

list_tables() {
    echo "📋 Database Tables:"
    echo "------------------"
    
    if [ -f "voiceflow.db" ]; then
        sqlite3 voiceflow.db ".tables"
        
        echo -e "\nTable schemas:"
        sqlite3 voiceflow.db ".schema" 2>/dev/null
    else
        echo "❌ Database file not found"
    fi
}

full_reset() {
    echo "🚀 Performing full reset..."
    echo "This will:"
    echo "- Delete the database file"
    echo "- Clear upload directories"
    echo "- Require server restart for memory cleanup"
    echo ""
    read -p "Are you sure? This will delete ALL data! (y/N): " confirm
    
    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        reset_database
        clear_session_agents
        echo "🎉 Full reset complete!"
    else
        echo "❌ Reset cancelled"
    fi
}

# Main script execution
while true; do
    show_menu
    
    case $choice in
        1)
            reset_database
            ;;
        2)
            show_database_contents
            ;;
        3)
            clear_session_agents
            ;;
        4)
            check_database_size
            ;;
        5)
            list_tables
            ;;
        6)
            full_reset
            ;;
        7)
            echo "👋 Goodbye!"
            exit 0
            ;;
        *)
            echo "❌ Invalid option. Please choose 1-7."
            ;;
    esac
    
    echo ""
    read -p "Press Enter to continue..."
done