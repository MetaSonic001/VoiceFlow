// Tenant utilities for multi-tenant operations
import { NextRequest } from 'next/server';

export function getTenantFromRequest(req: NextRequest): string | null {
  return req.headers.get('x-tenant-id') || req.headers.get('x-tenant-context');
}

export function validateTenantAccess(userTenantId: string | null, requestTenantId: string | null): boolean {
  if (!requestTenantId) return false;
  if (!userTenantId) return false;
  return userTenantId === requestTenantId;
}

export interface TenantContext {
  tenantId: string;
  userId: string;
  brandId?: string;
}