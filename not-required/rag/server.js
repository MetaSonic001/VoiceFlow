// Backend WebSocket Server for FR CRCE Information System (server.js)
import { GoogleGenerativeAI } from "@google/generative-ai";
import express from "express";
import { createServer } from "http";
import { WebSocketServer, WebSocket } from "ws";
import bodyParser from "body-parser";
import dotenv from "dotenv";
import cors from "cors";

dotenv.config();
const app = express();
const server = createServer(app);
const wss = new WebSocketServer({ server });

// Enable CORS for all routes
app.use(cors());

// Clients tracking
const clients = {
  dashboard: new Set(),
  admissionOfficers: new Set(),
  analytics: new Set(),
};

// In-memory storage for conversations and analytics
const conversationHistory = new Map();
const dailyStats = {
  totalCalls: 0,
  questionsAsked: {
    fees: 0,
    courses: 0,
    placements: 0,
    location: 0,
    facilities: 0,
    admission: 0,
    other: 0
  },
  averageCallDuration: 0,
  satisfactionRating: 0
};

// Middleware to parse Twilio webhooks
app.use(bodyParser.urlencoded({ extended: false }));
app.use(bodyParser.json());

if (!process.env.GEMINI_API_KEY) {
  console.error("GEMINI_API_KEY is not defined in environment variables");
  console.log("Please add GEMINI_API_KEY to your .env file");
  process.exit(1);
}

const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);

async function analyzeCollegeInquiry(conversationHistory) {
  try {
    const model = genAI.getGenerativeModel({
      model: "gemini-1.5-flash",
      safetySettings: [
        {
          category: "HARM_CATEGORY_HATE_SPEECH",
          threshold: "BLOCK_ONLY_HIGH",
        },
        {
          category: "HARM_CATEGORY_DANGEROUS_CONTENT",
          threshold: "BLOCK_ONLY_HIGH",
        },
      ],
    });

    const prompt = `Analyze this FR CRCE college information inquiry conversation and extract key details in JSON format:

Conversation:
${JSON.stringify(conversationHistory)}

Extract the following information EXACTLY in this JSON structure:
{
  "callerType": "prospective_student|parent|current_student|other",
  "primaryInterest": "fees|courses|placements|facilities|admission|location|other",
  "specificQuestions": ["list of specific questions asked"],
  "location": "caller's location if mentioned (city/state)",
  "name": "caller's name if mentioned",
  "contact": "phone/email if mentioned",
  "urgency": "high|medium|low",
  "followUpNeeded": true/false,
  "satisfactionLevel": "satisfied|partially_satisfied|unsatisfied|unknown",
  "summary": "Brief summary of the inquiry and information provided",
  "keyTopicsCovered": ["list of main topics discussed"],
  "additionalNotes": "any special requests or concerns mentioned"
}

Rules:
- If no specific detail is found, use "unknown" or empty array for lists
- Urgency: high = immediate admission deadline, medium = planning for next year, low = general inquiry
- Be precise and focus on college-related information needs
- Identify if caller needs follow-up from admission office`;

    const result = await model.generateContent(prompt);
    const response = await result.response;
    const text = response.text();
    
    console.log("AI Analysis Result:", text);
    
    // Clean and parse the JSON
    const cleanText = text
      .replace(/```json?/g, "")
      .replace(/```/g, "")
      .trim();
    
    return JSON.parse(cleanText);
  } catch (error) {
    console.error("Google AI Analysis Error:", error);
    return {
      callerType: "unknown",
      primaryInterest: "other",
      specificQuestions: [],
      location: "unknown",
      name: "unknown",
      contact: "unknown",
      urgency: "low",
      followUpNeeded: false,
      satisfactionLevel: "unknown",
      summary: "Failed to analyze inquiry details",
      keyTopicsCovered: [],
      additionalNotes: "Analysis error occurred"
    };
  }
}

// Main webhook endpoint for Twilio
app.post("/twilio-webhook", async (req, res) => {
  try {
    console.log("Received FR CRCE inquiry webhook:", req.body);
    const twilioData = req.body;
    const conversationData = twilioData.convo?.data || [];
    const callId = twilioData.id || `call-${Date.now()}`;
    
    // Analyze the conversation
    const aiAnalysis = await analyzeCollegeInquiry(conversationData);
    
    // Update daily statistics
    updateDailyStats(aiAnalysis);
    
    // Store conversation
    const enrichedData = {
      id: callId,
      timestamp: new Date().toISOString(),
      originalConversation: conversationData,
      aiAnalysis: aiAnalysis,
      status: "active",
      callDuration: calculateCallDuration(conversationData)
    };
    
    conversationHistory.set(callId, enrichedData);
    
    // Broadcast to all connected clients
    broadcastToDashboard({
      type: "college-inquiry-update",
      data: enrichedData,
    });
    
    // If follow-up needed, alert admission officers
    if (aiAnalysis.followUpNeeded || aiAnalysis.urgency === "high") {
      broadcastToAdmissionOfficers({
        type: "urgent-inquiry",
        data: {
          ...enrichedData,
          priority: aiAnalysis.urgency === "high" ? "urgent" : "follow-up-needed"
        }
      });
    }
    
    res.status(200).json({
      success: true,
      message: "FR CRCE inquiry processed successfully",
      callId: callId
    });
    
  } catch (error) {
    console.error("Webhook processing error:", error);
    
    // Send fallback data to dashboard
    broadcastToDashboard({
      type: "college-inquiry-update",
      data: {
        id: `error-${Date.now()}`,
        timestamp: new Date().toISOString(),
        originalConversation: [
          {
            role: "assistant",
            content: "Welcome to FR CRCE information service. How can I help you?"
          }
        ],
        aiAnalysis: {
          callerType: "unknown",
          primaryInterest: "other",
          specificQuestions: [],
          location: "unknown",
          name: "unknown",
          urgency: "low",
          summary: "Failed to process inquiry details",
          satisfactionLevel: "unknown",
          followUpNeeded: true,
          keyTopicsCovered: [],
          additionalNotes: "Processing error occurred"
        },
        status: "error"
      },
    });
    
    res.status(500).json({
      success: false,
      message: "Processing error occurred"
    });
  }
});

// Analytics endpoint
app.get("/analytics", (req, res) => {
  const analytics = {
    dailyStats: dailyStats,
    totalConversations: conversationHistory.size,
    recentInquiries: Array.from(conversationHistory.values())
      .slice(-10)
      .map(conv => ({
        id: conv.id,
        timestamp: conv.timestamp,
        primaryInterest: conv.aiAnalysis.primaryInterest,
        urgency: conv.aiAnalysis.urgency,
        satisfactionLevel: conv.aiAnalysis.satisfactionLevel
      }))
  };
  
  res.json(analytics);
});

// Get specific conversation
app.get("/conversation/:id", (req, res) => {
  const conversation = conversationHistory.get(req.params.id);
  if (conversation) {
    res.json(conversation);
  } else {
    res.status(404).json({ error: "Conversation not found" });
  }
});

// Get all conversations with filtering
app.get("/conversations", (req, res) => {
  const { urgency, primaryInterest, limit = 50 } = req.query;
  let conversations = Array.from(conversationHistory.values());
  
  // Apply filters
  if (urgency) {
    conversations = conversations.filter(conv => 
      conv.aiAnalysis.urgency === urgency
    );
  }
  
  if (primaryInterest) {
    conversations = conversations.filter(conv => 
      conv.aiAnalysis.primaryInterest === primaryInterest
    );
  }
  
  // Sort by timestamp (newest first) and limit
  conversations = conversations
    .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
    .slice(0, parseInt(limit));
  
  res.json({
    total: conversations.length,
    conversations: conversations
  });
});

// WebSocket connection handler
wss.on("connection", (ws, req) => {
  const clientType = new URL(
    req.url,
    `http://${req.headers.host}`,
  ).searchParams.get("type");

  // Add client to appropriate group
  if (clientType === "dashboard") {
    clients.dashboard.add(ws);
    console.log("Dashboard client connected");
    
    // Send current stats to new dashboard client
    ws.send(JSON.stringify({
      type: "initial-data",
      data: {
        dailyStats: dailyStats,
        recentConversations: Array.from(conversationHistory.values()).slice(-5)
      }
    }));
    
  } else if (clientType === "admission-officer") {
    clients.admissionOfficers.add(ws);
    console.log("Admission officer client connected");
    
  } else if (clientType === "analytics") {
    clients.analytics.add(ws);
    console.log("Analytics client connected");
  }

  // Message handling
  ws.on("message", (message) => {
    try {
      const parsedMessage = JSON.parse(message);
      
      // Handle different message types
      switch (parsedMessage.type) {
        case "update-conversation-status":
          updateConversationStatus(parsedMessage.data);
          break;
        case "request-analytics":
          sendAnalytics(ws);
          break;
        case "mark-follow-up-complete":
          markFollowUpComplete(parsedMessage.data.conversationId);
          break;
        default:
          console.log("Unknown message type:", parsedMessage.type);
      }
      
    } catch (error) {
      console.error("Message parsing error:", error);
    }
  });

  // Connection close handler
  ws.on("close", () => {
    clients.dashboard.delete(ws);
    clients.admissionOfficers.delete(ws);
    clients.analytics.delete(ws);
  });
});

// Utility functions
function updateDailyStats(analysis) {
  dailyStats.totalCalls += 1;
  
  // Update question categories
  if (dailyStats.questionsAsked[analysis.primaryInterest]) {
    dailyStats.questionsAsked[analysis.primaryInterest] += 1;
  } else {
    dailyStats.questionsAsked.other += 1;
  }
}

function calculateCallDuration(conversation) {
  // Estimate call duration based on conversation length
  const messageCount = conversation.length;
  return Math.max(1, Math.floor(messageCount * 0.5)); // Rough estimate in minutes
}

function updateConversationStatus(data) {
  const conversation = conversationHistory.get(data.conversationId);
  if (conversation) {
    conversation.status = data.status;
    conversation.notes = data.notes || conversation.notes;
    
    broadcastToDashboard({
      type: "conversation-status-updated",
      data: conversation
    });
  }
}

function markFollowUpComplete(conversationId) {
  const conversation = conversationHistory.get(conversationId);
  if (conversation) {
    conversation.aiAnalysis.followUpNeeded = false;
    conversation.status = "completed";
    
    broadcastToDashboard({
      type: "follow-up-completed",
      data: conversation
    });
  }
}

function sendAnalytics(ws) {
  const analytics = {
    dailyStats: dailyStats,
    totalConversations: conversationHistory.size,
    urgentInquiries: Array.from(conversationHistory.values())
      .filter(conv => conv.aiAnalysis.urgency === "high").length,
    followUpNeeded: Array.from(conversationHistory.values())
      .filter(conv => conv.aiAnalysis.followUpNeeded).length
  };
  
  ws.send(JSON.stringify({
    type: "analytics-data",
    data: analytics
  }));
}

// Broadcast utility functions
function broadcastToDashboard(message) {
  clients.dashboard.forEach((client) => {
    if (client.readyState === WebSocket.OPEN) {
      console.log("Broadcasting to dashboard:", message.type);
      client.send(JSON.stringify(message));
    }
  });
}

function broadcastToAdmissionOfficers(message) {
  clients.admissionOfficers.forEach((client) => {
    if (client.readyState === WebSocket.OPEN) {
      console.log("Broadcasting to admission officers:", message.type);
      client.send(JSON.stringify(message));
    }
  });
}

function broadcastToAnalytics(message) {
  clients.analytics.forEach((client) => {
    if (client.readyState === WebSocket.OPEN) {
      client.send(JSON.stringify(message));
    }
  });
}

// Health check endpoint
app.get("/health", (req, res) => {
  res.json({
    status: "healthy",
    timestamp: new Date().toISOString(),
    connections: {
      dashboard: clients.dashboard.size,
      admissionOfficers: clients.admissionOfficers.size,
      analytics: clients.analytics.size
    },
    stats: dailyStats
  });
});

// Start server
const PORT = process.env.PORT || 8080;
server.listen(PORT, () => {
  console.log(`FR CRCE Information System WebSocket Server running on port ${PORT}`);
  console.log(`WebSocket endpoints:`);
  console.log(`- Dashboard: ws://localhost:${PORT}?type=dashboard`);
  console.log(`- Admission Officers: ws://localhost:${PORT}?type=admission-officer`);
  console.log(`- Analytics: ws://localhost:${PORT}?type=analytics`);
  console.log(`HTTP endpoints:`);
  console.log(`- Webhook: http://localhost:${PORT}/twilio-webhook`);
  console.log(`- Analytics: http://localhost:${PORT}/analytics`);
  console.log(`- Health: http://localhost:${PORT}/health`);
});