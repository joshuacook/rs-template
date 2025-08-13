import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Switch,
  TouchableOpacity,
  ScrollView,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useApi } from '../contexts/ApiContext';

export default function SettingsScreen() {
  const { apiUrl } = useApi();
  const [notifications, setNotifications] = useState(true);
  const [darkMode, setDarkMode] = useState(false);
  const [autoSync, setAutoSync] = useState(true);

  const handleAbout = () => {
    Alert.alert(
      'About RS Template',
      'Version 1.0.0\n\nA template mobile app for testing Cloud Run services.\n\nBuilt with React Native and Expo.',
      [{ text: 'OK' }]
    );
  };

  const handleSupport = () => {
    Alert.alert(
      'Support',
      'For support, please contact:\nsupport@radicalsymmetry.com',
      [{ text: 'OK' }]
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Preferences</Text>
          
          <View style={styles.settingRow}>
            <View style={styles.settingInfo}>
              <Ionicons name="notifications-outline" size={24} color="#0066cc" />
              <Text style={styles.settingText}>Push Notifications</Text>
            </View>
            <Switch
              value={notifications}
              onValueChange={setNotifications}
              trackColor={{ false: '#767577', true: '#81b0ff' }}
              thumbColor={notifications ? '#0066cc' : '#f4f3f4'}
            />
          </View>
          
          <View style={styles.settingRow}>
            <View style={styles.settingInfo}>
              <Ionicons name="moon-outline" size={24} color="#0066cc" />
              <Text style={styles.settingText}>Dark Mode</Text>
            </View>
            <Switch
              value={darkMode}
              onValueChange={setDarkMode}
              trackColor={{ false: '#767577', true: '#81b0ff' }}
              thumbColor={darkMode ? '#0066cc' : '#f4f3f4'}
            />
          </View>
          
          <View style={styles.settingRow}>
            <View style={styles.settingInfo}>
              <Ionicons name="sync-outline" size={24} color="#0066cc" />
              <Text style={styles.settingText}>Auto Sync</Text>
            </View>
            <Switch
              value={autoSync}
              onValueChange={setAutoSync}
              trackColor={{ false: '#767577', true: '#81b0ff' }}
              thumbColor={autoSync ? '#0066cc' : '#f4f3f4'}
            />
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>API Configuration</Text>
          <View style={styles.apiInfo}>
            <Text style={styles.apiLabel}>Current Endpoint:</Text>
            <Text style={styles.apiUrl}>{apiUrl}</Text>
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Information</Text>
          
          <TouchableOpacity style={styles.infoButton} onPress={handleAbout}>
            <Ionicons name="information-circle-outline" size={24} color="#0066cc" />
            <Text style={styles.infoText}>About</Text>
            <Ionicons name="chevron-forward" size={24} color="#999" />
          </TouchableOpacity>
          
          <TouchableOpacity style={styles.infoButton} onPress={handleSupport}>
            <Ionicons name="help-circle-outline" size={24} color="#0066cc" />
            <Text style={styles.infoText}>Support</Text>
            <Ionicons name="chevron-forward" size={24} color="#999" />
          </TouchableOpacity>
          
          <TouchableOpacity style={styles.infoButton}>
            <Ionicons name="document-text-outline" size={24} color="#0066cc" />
            <Text style={styles.infoText}>Terms & Privacy</Text>
            <Ionicons name="chevron-forward" size={24} color="#999" />
          </TouchableOpacity>
        </View>

        <View style={styles.footer}>
          <Text style={styles.footerText}>RS Template Mobile</Text>
          <Text style={styles.versionText}>Version 1.0.0</Text>
        </View>
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
  section: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    marginBottom: 16,
  },
  settingRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  settingInfo: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  settingText: {
    fontSize: 16,
    color: '#333',
    marginLeft: 12,
  },
  apiInfo: {
    paddingVertical: 8,
  },
  apiLabel: {
    fontSize: 14,
    color: '#666',
    marginBottom: 4,
  },
  apiUrl: {
    fontSize: 12,
    color: '#0066cc',
    fontFamily: 'monospace',
  },
  infoButton: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  infoText: {
    flex: 1,
    fontSize: 16,
    color: '#333',
    marginLeft: 12,
  },
  footer: {
    alignItems: 'center',
    marginTop: 32,
    marginBottom: 16,
  },
  footerText: {
    fontSize: 14,
    color: '#666',
    marginBottom: 4,
  },
  versionText: {
    fontSize: 12,
    color: '#999',
  },
});