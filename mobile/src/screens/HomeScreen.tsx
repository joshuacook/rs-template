import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  RefreshControl,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuth } from '../contexts/AuthContext';
import { useApi } from '../contexts/ApiContext';

export default function HomeScreen() {
  const { user } = useAuth();
  const { get, post } = useApi();
  const [refreshing, setRefreshing] = useState(false);
  const [healthStatus, setHealthStatus] = useState<any>(null);
  const [aiResponse, setAiResponse] = useState<string>('');

  useEffect(() => {
    checkHealth();
  }, []);

  const checkHealth = async () => {
    try {
      const health = await get('/health');
      setHealthStatus(health);
    } catch (error) {
      console.error('Health check failed:', error);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await checkHealth();
    setRefreshing(false);
  };

  const testAI = async () => {
    try {
      const response = await post('/ai/chat', {
        messages: [
          { role: 'user', content: 'Hello, AI! Tell me a fun fact.' }
        ],
        max_tokens: 150
      });
      setAiResponse(response.response || response.choices?.[0]?.message?.content || 'No response from AI');
    } catch (error) {
      Alert.alert('Error', 'Failed to get AI response');
    }
  };

  const testFileUpload = async () => {
    Alert.alert(
      'File Upload',
      'File upload functionality would be implemented here with image picker integration.'
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
      >
        <View style={styles.header}>
          <Text style={styles.title}>Welcome, {user?.name || 'User'}!</Text>
          <Text style={styles.subtitle}>RS Template Mobile App</Text>
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>System Status</Text>
          {healthStatus ? (
            <View>
              <Text style={styles.statusText}>
                Gateway: {healthStatus.status || 'Unknown'}
              </Text>
              <Text style={styles.statusText}>
                Version: {healthStatus.version || 'Unknown'}
              </Text>
              <Text style={styles.statusText}>
                Environment: {healthStatus.environment || 'Unknown'}
              </Text>
            </View>
          ) : (
            <Text style={styles.statusText}>Loading...</Text>
          )}
        </View>

        <View style={styles.actions}>
          <TouchableOpacity style={styles.actionButton} onPress={testAI}>
            <Text style={styles.actionButtonText}>Test AI Service</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.actionButton} onPress={testFileUpload}>
            <Text style={styles.actionButtonText}>Test File Upload</Text>
          </TouchableOpacity>
        </View>

        {aiResponse ? (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>AI Response</Text>
            <Text style={styles.aiText}>{aiResponse}</Text>
          </View>
        ) : null}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  scrollContent: {
    padding: 20,
  },
  header: {
    marginBottom: 24,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 16,
    color: '#666',
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.1,
    shadowRadius: 3.84,
    elevation: 5,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    marginBottom: 12,
  },
  statusText: {
    fontSize: 14,
    color: '#666',
    marginBottom: 4,
  },
  actions: {
    marginVertical: 16,
  },
  actionButton: {
    backgroundColor: '#0066cc',
    borderRadius: 8,
    padding: 16,
    alignItems: 'center',
    marginBottom: 12,
  },
  actionButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  aiText: {
    fontSize: 14,
    color: '#333',
    lineHeight: 20,
  },
});