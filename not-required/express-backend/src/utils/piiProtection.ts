export interface PIIResult {
  hasPII: boolean;
  redactedText: string;
  detectedEntities: Array<{
    type: string;
    value: string;
    start: number;
    end: number;
    confidence: number;
  }>;
}

export class PIIProtection {
  // Common PII patterns
  private static readonly PATTERNS = {
    // Email addresses
    email: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g,

    // Phone numbers (various formats)
    phone: /(\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b/g,

    // Social Security Numbers
    ssn: /\b\d{3}[-]?\d{2}[-]?\d{4}\b/g,

    // Credit card numbers (basic pattern)
    creditCard: /\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b/g,

    // IP addresses
    ipAddress: /\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b/g,

    // API keys (common patterns)
    apiKey: /\b[A-Za-z0-9]{20,}\b/g, // Generic long alphanumeric strings

    // URLs with potential sensitive info
    sensitiveUrl: /\bhttps?:\/\/[^\s]*?(?:password|token|key|secret)[^\s]*/gi,
  };

  // Custom entity recognition for names, addresses, etc.
  private static readonly CUSTOM_PATTERNS = {
    // US Addresses (basic pattern)
    address: /\b\d+\s+[A-Za-z0-9\s,.-]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Place|Pl|Court|Ct)\b/gi,

    // Dates of birth (various formats)
    dob: /\b(?:\d{1,2}[-\/]\d{1,2}[-\/]\d{2,4}|\d{2,4}[-\/]\d{1,2}[-\/]\d{1,2})\b/g,
  };

  static detectAndRedact(text: string): PIIResult {
    let redactedText = text;
    const detectedEntities: PIIResult['detectedEntities'] = [];

    // Check each pattern
    Object.entries(this.PATTERNS).forEach(([type, pattern]) => {
      let match;
      while ((match = pattern.exec(text)) !== null) {
        const value = match[0];
        const start = match.index;
        const end = start + value.length;

        // Skip if this is part of a previously detected entity
        const isOverlapping = detectedEntities.some(entity =>
          (start >= entity.start && start < entity.end) ||
          (end > entity.start && end <= entity.end) ||
          (start <= entity.start && end >= entity.end)
        );

        if (!isOverlapping) {
          detectedEntities.push({
            type,
            value,
            start,
            end,
            confidence: this.getConfidence(type, value)
          });
        }
      }
    });

    // Check custom patterns
    Object.entries(this.CUSTOM_PATTERNS).forEach(([type, pattern]) => {
      let match;
      while ((match = pattern.exec(text)) !== null) {
        const value = match[0];
        const start = match.index;
        const end = start + value.length;

        const isOverlapping = detectedEntities.some(entity =>
          (start >= entity.start && start < entity.end) ||
          (end > entity.start && end <= entity.end) ||
          (start <= entity.start && end >= entity.end)
        );

        if (!isOverlapping) {
          detectedEntities.push({
            type,
            value,
            start,
            end,
            confidence: 0.7 // Lower confidence for custom patterns
          });
        }
      }
    });

    // Sort entities by position and redact from end to start to maintain indices
    detectedEntities.sort((a, b) => b.start - a.start);

    detectedEntities.forEach(entity => {
      const mask = this.getMask(entity.type);
      redactedText = redactedText.substring(0, entity.start) +
                    mask +
                    redactedText.substring(entity.end);
    });

    return {
      hasPII: detectedEntities.length > 0,
      redactedText,
      detectedEntities
    };
  }

  private static getConfidence(type: string, value: string): number {
    switch (type) {
      case 'email':
        return value.includes('@') && value.includes('.') ? 0.95 : 0.8;
      case 'phone':
        return value.replace(/[-.\s()]/g, '').length >= 10 ? 0.9 : 0.7;
      case 'ssn':
        return 0.95;
      case 'creditCard':
        return this.isValidCreditCard(value) ? 0.95 : 0.8;
      case 'ipAddress':
        return this.isValidIPAddress(value) ? 0.9 : 0.7;
      case 'apiKey':
        return value.length > 25 ? 0.8 : 0.6;
      case 'sensitiveUrl':
        return 0.9;
      default:
        return 0.7;
    }
  }

  private static getMask(type: string): string {
    switch (type) {
      case 'email':
        return '[EMAIL REDACTED]';
      case 'phone':
        return '[PHONE REDACTED]';
      case 'ssn':
        return '[SSN REDACTED]';
      case 'creditCard':
        return '[CREDIT CARD REDACTED]';
      case 'ipAddress':
        return '[IP ADDRESS REDACTED]';
      case 'apiKey':
        return '[API KEY REDACTED]';
      case 'sensitiveUrl':
        return '[SENSITIVE URL REDACTED]';
      case 'address':
        return '[ADDRESS REDACTED]';
      case 'dob':
        return '[DATE OF BIRTH REDACTED]';
      default:
        return '[REDACTED]';
    }
  }

  private static isValidCreditCard(value: string): boolean {
    const cleanValue = value.replace(/[- ]/g, '');
    if (cleanValue.length < 13 || cleanValue.length > 19) return false;

    // Luhn algorithm
    let sum = 0;
    let shouldDouble = false;

    for (let i = cleanValue.length - 1; i >= 0; i--) {
      let digit = parseInt(cleanValue.charAt(i), 10);

      if (shouldDouble) {
        digit *= 2;
        if (digit > 9) digit -= 9;
      }

      sum += digit;
      shouldDouble = !shouldDouble;
    }

    return sum % 10 === 0;
  }

  private static isValidIPAddress(value: string): boolean {
    const parts = value.split('.');
    if (parts.length !== 4) return false;

    return parts.every(part => {
      const num = parseInt(part, 10);
      return num >= 0 && num <= 255 && part === num.toString();
    });
  }

  static sanitizeObject(obj: any): any {
    if (typeof obj === 'string') {
      return this.detectAndRedact(obj).redactedText;
    }

    if (Array.isArray(obj)) {
      return obj.map(item => this.sanitizeObject(item));
    }

    if (obj && typeof obj === 'object') {
      const sanitized: any = {};
      for (const [key, value] of Object.entries(obj)) {
        // Skip sensitive keys entirely
        if (this.isSensitiveKey(key)) {
          sanitized[key] = '[REDACTED]';
        } else {
          sanitized[key] = this.sanitizeObject(value);
        }
      }
      return sanitized;
    }

    return obj;
  }

  private static isSensitiveKey(key: string): boolean {
    const sensitiveKeys = [
      'password', 'token', 'secret', 'key', 'apikey', 'auth',
      'ssn', 'socialsecurity', 'creditcard', 'cardnumber'
    ];

    return sensitiveKeys.some(sensitive =>
      key.toLowerCase().includes(sensitive)
    );
  }
}

export default PIIProtection;