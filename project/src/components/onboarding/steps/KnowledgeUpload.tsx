import React, { useState } from 'react';
import { Upload, FileText, Link, Database, Plus, X } from 'lucide-react';
import { Button } from '../../ui/Button';
import { Input } from '../../ui/Input';
import { apiClient } from '../../../config/api';

interface KnowledgeUploadProps {
  data: Record<string, any>;
  onDataChange: (data: Record<string, any>) => void;
  onNext: () => void;
}

export const KnowledgeUpload: React.FC<KnowledgeUploadProps> = ({ data, onDataChange, onNext }) => {
  const [uploadedFiles, setUploadedFiles] = useState<string[]>(data.uploadedFiles || []);
  const [websiteUrls, setWebsiteUrls] = useState<string[]>(data.websiteUrls || ['']);
  const [dragActive, setDragActive] = useState(false);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const files = Array.from(e.dataTransfer.files).map(file => file.name);
      setUploadedFiles(prev => [...prev, ...files]);
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const files = Array.from(e.target.files).map(file => file.name);
      setUploadedFiles(prev => [...prev, ...files]);
      
      // Upload files to backend
      const formData = new FormData();
      Array.from(e.target.files).forEach(file => {
        formData.append('files', file);
      });
      
      apiClient.uploadKnowledge(formData).catch(error => {
        console.error('File upload failed:', error);
      });
    }
  };

  const removeFile = (index: number) => {
    setUploadedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const addUrlField = () => {
    setWebsiteUrls(prev => [...prev, '']);
  };

  const updateUrl = (index: number, value: string) => {
    setWebsiteUrls(prev => prev.map((url, i) => i === index ? value : url));
  };

  const removeUrl = (index: number) => {
    setWebsiteUrls(prev => prev.filter((_, i) => i !== index));
  };

  const handleNext = () => {
    onDataChange({
      uploadedFiles: uploadedFiles.filter(file => file.trim() !== ''),
      websiteUrls: websiteUrls.filter(url => url.trim() !== '')
    });
    onNext();
  };

  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-bold text-gray-900">Upload your knowledge base</h2>
        <p className="text-gray-600">Add documents, FAQs, and resources for your agent to learn from</p>
      </div>

      <div className="grid lg:grid-cols-2 gap-8">
        {/* File Upload */}
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-gray-900 flex items-center">
            <FileText className="h-5 w-5 mr-2" />
            Documents & Files
          </h3>
          
          <div
            className={`relative border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
              dragActive 
                ? 'border-blue-500 bg-blue-50' 
                : 'border-gray-300 hover:border-gray-400'
            }`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            <Upload className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600 mb-2">
              Drag and drop files here, or <span className="text-blue-600">browse</span>
            </p>
            <p className="text-sm text-gray-500">
              Supports PDF, DOC, TXT, CSV, and more
            </p>
            <input
              type="file"
              multiple
              onChange={handleFileUpload}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            />
          </div>

          {uploadedFiles.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-gray-700">Uploaded Files:</h4>
              {uploadedFiles.map((file, index) => (
                <div key={index} className="flex items-center justify-between bg-gray-50 rounded-lg p-3">
                  <div className="flex items-center space-x-2">
                    <FileText className="h-4 w-4 text-gray-500" />
                    <span className="text-sm text-gray-900">{file}</span>
                  </div>
                  <button
                    onClick={() => removeFile(index)}
                    className="text-gray-400 hover:text-red-600"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Website URLs */}
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-gray-900 flex items-center">
            <Link className="h-5 w-5 mr-2" />
            Website URLs
          </h3>
          
          <div className="space-y-3">
            {websiteUrls.map((url, index) => (
              <div key={index} className="flex items-center space-x-2">
                <Input
                  type="url"
                  value={url}
                  onChange={(e) => updateUrl(index, e.target.value)}
                  placeholder="https://yourcompany.com/faq"
                  className="flex-1"
                />
                {websiteUrls.length > 1 && (
                  <button
                    onClick={() => removeUrl(index)}
                    className="text-gray-400 hover:text-red-600 p-2"
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}
              </div>
            ))}
            
            <Button
              variant="outline"
              size="sm"
              onClick={addUrlField}
              className="w-full"
            >
              <Plus className="h-4 w-4 mr-2" />
              Add Another URL
            </Button>
          </div>
        </div>
      </div>

      {/* Integration Options */}
      <div className="border-t pt-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
          <Database className="h-5 w-5 mr-2" />
          Integrations (Coming Soon)
        </h3>
        
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {['Google Drive', 'Notion', 'Confluence', 'Zendesk'].map(integration => (
            <div key={integration} className="bg-gray-50 rounded-lg p-4 text-center opacity-50">
              <div className="w-8 h-8 bg-gray-300 rounded mx-auto mb-2"></div>
              <span className="text-sm text-gray-600">{integration}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="flex justify-end pt-6">
        <Button onClick={handleNext}>
          Continue to Voice Setup
        </Button>
      </div>
    </div>
  );
};