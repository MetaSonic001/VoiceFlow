import { Client } from 'minio';
import { Readable } from 'stream';

export interface MinIOConfig {
  endPoint: string;
  port: number;
  useSSL: boolean;
  accessKey: string;
  secretKey: string;
  region?: string;
}

export class MinioService {
  private client: Client;
  private bucketName: string;

  constructor(config: MinIOConfig, bucketName: string = 'documents') {
    this.client = new Client(config);
    this.bucketName = bucketName;
    this.initializeBucket();
  }

  private async initializeBucket(): Promise<void> {
    try {
      const exists = await this.client.bucketExists(this.bucketName);
      if (!exists) {
        await this.client.makeBucket(this.bucketName, 'us-east-1');
        console.log(`Created bucket: ${this.bucketName}`);
      }
    } catch (error) {
      console.error('Error initializing MinIO bucket:', error);
      throw error;
    }
  }

  async uploadFile(
    tenantId: string,
    fileName: string,
    fileStream: Readable,
    contentType: string,
    size?: number
  ): Promise<string> {
    try {
      const objectName = `${tenantId}/${Date.now()}-${fileName}`;

      await this.client.putObject(
        this.bucketName,
        objectName,
        fileStream,
        size,
        { 'Content-Type': contentType }
      );

      return objectName;
    } catch (error) {
      console.error('Error uploading file to MinIO:', error);
      throw new Error('Failed to upload file');
    }
  }

  async uploadBuffer(
    tenantId: string,
    buffer: Buffer,
    fileName: string,
    contentType: string
  ): Promise<string> {
    try {
      const objectName = `${tenantId}/${Date.now()}-${fileName}`;

      await this.client.putObject(
        this.bucketName,
        objectName,
        buffer,
        buffer.length,
        { 'Content-Type': contentType }
      );

      return objectName;
    } catch (error) {
      console.error('Error uploading buffer to MinIO:', error);
      throw new Error('Failed to upload file');
    }
  }

  async downloadFile(tenantId: string, objectName: string): Promise<Readable> {
    try {
      return await this.client.getObject(this.bucketName, `${tenantId}/${objectName}`);
    } catch (error) {
      console.error('Error downloading file from MinIO:', error);
      throw new Error('Failed to download file');
    }
  }

  async deleteFile(tenantId: string, objectName: string): Promise<void> {
    try {
      await this.client.removeObject(this.bucketName, `${tenantId}/${objectName}`);
    } catch (error) {
      console.error('Error deleting file from MinIO:', error);
      throw new Error('Failed to delete file');
    }
  }

  async getFileUrl(tenantId: string, objectName: string, expirySeconds: number = 3600): Promise<string> {
    try {
      return await this.client.presignedGetObject(
        this.bucketName,
        `${tenantId}/${objectName}`,
        expirySeconds
      );
    } catch (error) {
      console.error('Error generating file URL:', error);
      throw new Error('Failed to generate file URL');
    }
  }

  async listTenantFiles(tenantId: string): Promise<string[]> {
    try {
      const objects: any[] = [];
      const stream = this.client.listObjects(this.bucketName, `${tenantId}/`, true);
      return new Promise((resolve, reject) => {
        stream.on('data', (obj) => objects.push(obj));
        stream.on('end', () => {
          const fileNames = objects.map(obj => obj.name || '').filter(name => name.startsWith(`${tenantId}/`));
          resolve(fileNames);
        });
        stream.on('error', (error) => {
          console.error('Error listing tenant files:', error);
          reject(new Error('Failed to list files'));
        });
      });
    } catch (error) {
      console.error('Error listing tenant files:', error);
      throw new Error('Failed to list files');
    }
  }

  async getFileStats(tenantId: string, objectName: string): Promise<any> {
    try {
      const stat = await this.client.statObject(this.bucketName, `${tenantId}/${objectName}`);
      return stat;
    } catch (error) {
      console.error('Error getting file stats:', error);
      throw new Error('Failed to get file stats');
    }
  }
}

// Create singleton instance
const minioConfig: MinIOConfig = {
  endPoint: process.env.MINIO_ENDPOINT || 'localhost',
  port: parseInt(process.env.MINIO_PORT || '9000'),
  useSSL: process.env.MINIO_USE_SSL === 'true',
  accessKey: process.env.MINIO_ACCESS_KEY || 'minioadmin',
  secretKey: process.env.MINIO_SECRET_KEY || 'minioadmin',
  region: process.env.MINIO_REGION
};

const minioService = new MinioService(minioConfig);

export default minioService;