import React, { useState, useEffect } from 'react';
import { Phone, Clock, TrendingUp, AlertCircle } from 'lucide-react';

interface AnalyticsData {
  activeCalls: number;
  totalCalls: number;
  averageCallDuration: number;
  successRate: number;
  callHistory: Array<{
    id: string;
    timestamp: string;
    duration: number;
    status: 'success' | 'failed' | 'in-progress';
    phoneNumber: string;
  }>;
}

interface AnalyticsOverviewProps {
  wsData?: AnalyticsData;
}

const StatCard: React.FC<{
  title: string;
  value: string | number;
  icon: React.ReactNode;
  trend?: string;
  loading?: boolean;
}> = ({ title, value, icon, trend, loading }) => (
  <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
    <div className="flex items-center justify-between">
      <div>
        <p className="text-sm font-medium text-gray-600">{title}</p>
        <p className="text-2xl font-bold text-gray-900">
          {loading ? (
            <div className="animate-pulse bg-gray-200 h-8 w-16 rounded"></div>
          ) : (
            value
          )}
        </p>
        {trend && (
          <p className="text-xs text-green-600 mt-1">{trend}</p>
        )}
      </div>
      <div className="p-3 bg-blue-50 rounded-full">
        {icon}
      </div>
    </div>
  </div>
);

export const AnalyticsOverview: React.FC<AnalyticsOverviewProps> = ({ wsData }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Default data structure to prevent undefined errors
  const defaultData: AnalyticsData = {
    activeCalls: 0,
    totalCalls: 0,
    averageCallDuration: 0,
    successRate: 0,
    callHistory: []
  };

  // Use provided data or default data
  const data = wsData || defaultData;

  useEffect(() => {
    // Simulate loading state
    const timer = setTimeout(() => {
      setLoading(false);
    }, 1000);

    return () => clearTimeout(timer);
  }, []);

  // Format duration in minutes and seconds
  const formatDuration = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <div className="flex items-center">
          <AlertCircle className="h-5 w-5 text-red-600 mr-2" />
          <span className="text-red-800">Error loading analytics: {error}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Analytics Overview</h2>
        <div className="flex items-center space-x-2">
          <div className={`w-3 h-3 rounded-full ${wsData ? 'bg-green-500' : 'bg-gray-400'}`}></div>
          <span className="text-sm text-gray-600">
            {wsData ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Active Calls"
          value={data.activeCalls}
          icon={<Phone className="h-6 w-6 text-blue-600" />}
          loading={loading}
        />
        <StatCard
          title="Total Calls"
          value={data.totalCalls}
          icon={<TrendingUp className="h-6 w-6 text-green-600" />}
          trend="+12% from yesterday"
          loading={loading}
        />
        <StatCard
          title="Avg Duration"
          value={formatDuration(data.averageCallDuration)}
          icon={<Clock className="h-6 w-6 text-purple-600" />}
          loading={loading}
        />
        <StatCard
          title="Success Rate"
          value={`${data.successRate}%`}
          icon={<TrendingUp className="h-6 w-6 text-emerald-600" />}
          trend="+5% from yesterday"
          loading={loading}
        />
      </div>

      {/* Recent Calls Table */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">Recent Calls</h3>
        </div>
        <div className="overflow-x-auto">
          {loading ? (
            <div className="p-6">
              <div className="animate-pulse space-y-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="flex space-x-4">
                    <div className="h-4 bg-gray-200 rounded w-1/4"></div>
                    <div className="h-4 bg-gray-200 rounded w-1/4"></div>
                    <div className="h-4 bg-gray-200 rounded w-1/4"></div>
                    <div className="h-4 bg-gray-200 rounded w-1/4"></div>
                  </div>
                ))}
              </div>
            </div>
          ) : data.callHistory && data.callHistory.length > 0 ? (
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Phone Number
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Time
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Duration
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {data.callHistory.map((call) => (
                  <tr key={call.id}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {call.phoneNumber}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(call.timestamp).toLocaleTimeString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatDuration(call.duration)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                          call.status === 'success'
                            ? 'bg-green-100 text-green-800'
                            : call.status === 'failed'
                            ? 'bg-red-100 text-red-800'
                            : 'bg-yellow-100 text-yellow-800'
                        }`}
                      >
                        {call.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="p-6 text-center">
              <p className="text-gray-500">No call history available</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};