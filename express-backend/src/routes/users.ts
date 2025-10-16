// User management API endpoints for the Express backend
// This would be added to the main Express server file

import express from 'express'
import { authenticateToken, requireAdmin } from '../middleware/auth'
import { body, validationResult } from 'express-validator'

const router = express.Router()

// Get all users (admin only)
router.get('/users', authenticateToken, requireAdmin, async (req: any, res) => {
  try {
    const { page = 1, limit = 10, search, role, status } = req.query

    // Mock users data - in real implementation, fetch from database with pagination
    const mockUsers = [
      {
        id: 'user-1',
        email: 'admin@voiceflow.com',
        name: 'Admin User',
        role: 'admin',
        status: 'active',
        lastLogin: '2024-01-15T10:00:00Z',
        createdAt: '2024-01-01T00:00:00Z',
        avatar: null
      },
      {
        id: 'user-2',
        email: 'john.doe@company.com',
        name: 'John Doe',
        role: 'user',
        status: 'active',
        lastLogin: '2024-01-14T15:30:00Z',
        createdAt: '2024-01-05T09:00:00Z',
        avatar: null
      },
      {
        id: 'user-3',
        email: 'jane.smith@company.com',
        name: 'Jane Smith',
        role: 'user',
        status: 'inactive',
        lastLogin: '2024-01-10T14:20:00Z',
        createdAt: '2024-01-03T11:15:00Z',
        avatar: null
      }
    ]

    // Apply filters
    let filteredUsers = mockUsers

    if (search) {
      filteredUsers = filteredUsers.filter(user =>
        user.name.toLowerCase().includes(search.toLowerCase()) ||
        user.email.toLowerCase().includes(search.toLowerCase())
      )
    }

    if (role) {
      filteredUsers = filteredUsers.filter(user => user.role === role)
    }

    if (status) {
      filteredUsers = filteredUsers.filter(user => user.status === status)
    }

    // Apply pagination
    const startIndex = (page - 1) * limit
    const endIndex = startIndex + limit
    const paginatedUsers = filteredUsers.slice(startIndex, endIndex)

    res.json({
      users: paginatedUsers,
      pagination: {
        page: parseInt(page),
        limit: parseInt(limit),
        total: filteredUsers.length,
        pages: Math.ceil(filteredUsers.length / limit)
      }
    })
  } catch (error) {
    console.error('Error fetching users:', error)
    res.status(500).json({ error: 'Failed to fetch users' })
  }
})

// Get user by ID
router.get('/users/:userId', authenticateToken, async (req: any, res) => {
  try {
    const { userId } = req.params
    const requestingUserId = req.user.id

    // Users can view their own profile, admins can view any profile
    if (userId !== requestingUserId && req.user.role !== 'admin') {
      return res.status(403).json({ error: 'Access denied' })
    }

    // Mock user data - in real implementation, fetch from database
    const mockUser = {
      id: userId,
      email: 'user@voiceflow.com',
      name: 'Sample User',
      role: 'user',
      status: 'active',
      lastLogin: '2024-01-15T10:00:00Z',
      createdAt: '2024-01-01T00:00:00Z',
      avatar: null,
      profile: {
        phone: '+1234567890',
        department: 'Engineering',
        jobTitle: 'Developer'
      }
    }

    res.json(mockUser)
  } catch (error) {
    console.error('Error fetching user:', error)
    res.status(500).json({ error: 'Failed to fetch user' })
  }
})

// Update user
router.put('/users/:userId', authenticateToken, [
  body('name').optional().isString().notEmpty(),
  body('email').optional().isEmail(),
  body('role').optional().isIn(['user', 'admin']),
  body('status').optional().isIn(['active', 'inactive', 'suspended'])
], async (req: any, res) => {
  try {
    const errors = validationResult(req)
    if (!errors.isEmpty()) {
      return res.status(400).json({ errors: errors.array() })
    }

    const { userId } = req.params
    const requestingUserId = req.user.id
    const updates = req.body

    // Users can update their own profile, admins can update any profile
    if (userId !== requestingUserId && req.user.role !== 'admin') {
      return res.status(403).json({ error: 'Access denied' })
    }

    // Non-admin users cannot change role or status
    if (req.user.role !== 'admin' && (updates.role || updates.status)) {
      return res.status(403).json({ error: 'Insufficient permissions' })
    }

    // Mock user update - in real implementation, update database
    console.log(`Updating user ${userId}:`, updates)

    res.json({
      message: 'User updated successfully',
      user: {
        id: userId,
        ...updates
      }
    })
  } catch (error) {
    console.error('Error updating user:', error)
    res.status(500).json({ error: 'Failed to update user' })
  }
})

// Delete user (admin only)
router.delete('/users/:userId', authenticateToken, requireAdmin, async (req: any, res) => {
  try {
    const { userId } = req.params

    // Prevent deleting self
    if (userId === req.user.id) {
      return res.status(400).json({ error: 'Cannot delete your own account' })
    }

    // Mock user deletion - in real implementation, soft delete in database
    console.log(`Deleting user ${userId}`)

    res.json({ message: 'User deleted successfully' })
  } catch (error) {
    console.error('Error deleting user:', error)
    res.status(500).json({ error: 'Failed to delete user' })
  }
})

// Create user (admin only)
router.post('/users', authenticateToken, requireAdmin, [
  body('name').isString().notEmpty(),
  body('email').isEmail(),
  body('role').optional().isIn(['user', 'admin']),
  body('password').isString().isLength({ min: 8 })
], async (req: any, res) => {
  try {
    const errors = validationResult(req)
    if (!errors.isEmpty()) {
      return res.status(400).json({ errors: errors.array() })
    }

    const { name, email, role = 'user', password } = req.body

    // Mock user creation - in real implementation, create in database
    const newUser = {
      id: `user-${Date.now()}`,
      name,
      email,
      role,
      status: 'active',
      createdAt: new Date().toISOString(),
      avatar: null
    }

    console.log('Creating new user:', newUser)

    res.status(201).json(newUser)
  } catch (error) {
    console.error('Error creating user:', error)
    res.status(500).json({ error: 'Failed to create user' })
  }
})

// Bulk user operations (admin only)
router.post('/users/bulk', authenticateToken, requireAdmin, [
  body('operation').isIn(['activate', 'deactivate', 'delete']),
  body('userIds').isArray()
], async (req: any, res) => {
  try {
    const errors = validationResult(req)
    if (!errors.isEmpty()) {
      return res.status(400).json({ errors: errors.array() })
    }

    const { operation, userIds } = req.body

    // Mock bulk operation - in real implementation, perform bulk database operation
    console.log(`Bulk ${operation} for users:`, userIds)

    res.json({
      message: `Bulk ${operation} completed successfully`,
      affectedUsers: userIds.length
    })
  } catch (error) {
    console.error('Error performing bulk operation:', error)
    res.status(500).json({ error: 'Failed to perform bulk operation' })
  }
})

export default router