import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Button } from './ui/button';
import { Input } from './ui/input';
import ChatInterface from './ChatInterface';
import { useAuth } from '../providers/authProvider';

interface DashboardProps {
  className?: string;
}

const Dashboard: React.FC<DashboardProps> = ({ className }) => {
  const { user } = useAuth();

  return (
    <div className={className}>
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Welcome back, {user?.name || 'User'}!</CardTitle>
          <CardDescription>
            Find the best deals and discounts near you.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <Input
              placeholder="Search for deals..."
              className="max-w-sm"
            />
            <Button>Search</Button>
          </div>
        </CardContent>
      </Card>

      <Tabs defaultValue="chat" className="space-y-4">
        <TabsList>
          <TabsTrigger value="chat">Chat</TabsTrigger>
          <TabsTrigger value="deals">Deals</TabsTrigger>
          <TabsTrigger value="saved">Saved</TabsTrigger>
        </TabsList>
        <TabsContent value="chat" className="space-y-4">
          <ChatInterface />
        </TabsContent>
        <TabsContent value="deals" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Latest Deals</CardTitle>
              <CardDescription>
                Browse through the most recent deals in your area.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {/* Add deals list component here */}
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="saved" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Saved Deals</CardTitle>
              <CardDescription>
                View and manage your saved deals.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {/* Add saved deals list component here */}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default Dashboard; 