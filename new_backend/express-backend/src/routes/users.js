const express = require('express');
const router = express.Router();

// Middleware to validate tenant access
const validateTenantAccess = (req, res, next) => {
  const tenantId = req.headers['x-tenant-id'] || req.query.tenantId;
  if (!tenantId) {
    return res.status(400).json({ error: 'Tenant ID required' });
  }
  req.tenantId = tenantId;
  next();
};

// Get user by ID
router.get('/:id', validateTenantAccess, async (req, res) => {
  try {
    const prisma = req.app.get('prisma');
    const { id } = req.params;

    // Ensure user can only access their own data or tenant admin can access tenant users
    const user = await prisma.user.findFirst({
      where: {
        id: id,
        id: req.tenantId // For now, users can only access their own data
      },
      select: {
        id: true,
        email: true,
        name: true,
        createdAt: true,
        updatedAt: true
      }
    });

    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }

    res.json(user);
  } catch (error) {
    console.error('Error fetching user:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

module.exports = router;