import * as ImagePicker from 'expo-image-picker';
import * as FileSystem from 'expo-file-system';

interface UploadOptions {
  baseUrl: string;
  token: string;
}

interface PickedImage {
  uri: string;
  type?: string;
  name?: string;
  base64?: string;
}

export class UploadService {
  /**
   * Request camera permissions
   */
  static async requestCameraPermissions(): Promise<boolean> {
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    return status === 'granted';
  }

  /**
   * Request media library permissions
   */
  static async requestMediaLibraryPermissions(): Promise<boolean> {
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    return status === 'granted';
  }

  /**
   * Pick image from library
   */
  static async pickImageFromLibrary(): Promise<PickedImage | null> {
    const hasPermission = await this.requestMediaLibraryPermissions();
    if (!hasPermission) {
      throw new Error('Permission to access media library was denied');
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      aspect: [4, 3],
      quality: 0.8,
      base64: false, // We'll upload as binary
    });

    if (!result.canceled && result.assets && result.assets.length > 0) {
      const asset = result.assets[0];
      return {
        uri: asset.uri,
        type: asset.mimeType || 'image/jpeg',
        name: asset.fileName || `photo_${Date.now()}.jpg`,
      };
    }

    return null;
  }

  /**
   * Take photo with camera
   */
  static async takePhoto(): Promise<PickedImage | null> {
    const hasPermission = await this.requestCameraPermissions();
    if (!hasPermission) {
      throw new Error('Permission to access camera was denied');
    }

    const result = await ImagePicker.launchCameraAsync({
      allowsEditing: true,
      aspect: [4, 3],
      quality: 0.8,
      base64: false,
    });

    if (!result.canceled && result.assets && result.assets.length > 0) {
      const asset = result.assets[0];
      return {
        uri: asset.uri,
        type: asset.mimeType || 'image/jpeg',
        name: `photo_${Date.now()}.jpg`,
      };
    }

    return null;
  }

  /**
   * Upload image to API
   */
  static async uploadImage(
    image: PickedImage,
    options: UploadOptions
  ): Promise<any> {
    // Create FormData
    const formData = new FormData();
    
    // Add the image file
    formData.append('file', {
      uri: image.uri,
      type: image.type || 'image/jpeg',
      name: image.name || 'upload.jpg',
    } as any);

    // Add metadata
    formData.append('metadata', JSON.stringify({
      uploadedAt: new Date().toISOString(),
      source: 'mobile',
    }));

    try {
      const response = await fetch(`${options.baseUrl}/api/files/upload`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${options.token}`,
          'Accept': 'application/json',
        },
        body: formData,
      });

      if (!response.ok) {
        const error = await response.text();
        throw new Error(`Upload failed: ${error}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Upload error:', error);
      throw error;
    }
  }

  /**
   * Upload image using FileSystem for more control
   */
  static async uploadImageWithFileSystem(
    image: PickedImage,
    options: UploadOptions
  ): Promise<any> {
    try {
      // Read file info
      const fileInfo = await FileSystem.getInfoAsync(image.uri);
      if (!fileInfo.exists) {
        throw new Error('File does not exist');
      }

      // Upload using FileSystem.uploadAsync
      const uploadResult = await FileSystem.uploadAsync(
        `${options.baseUrl}/api/files/upload`,
        image.uri,
        {
          fieldName: 'file',
          httpMethod: 'POST',
          uploadType: FileSystem.FileSystemUploadType.MULTIPART,
          headers: {
            'Authorization': `Bearer ${options.token}`,
            'Accept': 'application/json',
          },
          parameters: {
            metadata: JSON.stringify({
              uploadedAt: new Date().toISOString(),
              source: 'mobile',
              size: fileInfo.size,
            }),
          },
        }
      );

      if (uploadResult.status !== 200) {
        throw new Error(`Upload failed with status ${uploadResult.status}`);
      }

      return JSON.parse(uploadResult.body);
    } catch (error) {
      console.error('Upload error:', error);
      throw error;
    }
  }

  /**
   * Get download URL for a file
   */
  static async getDownloadUrl(
    fileId: string,
    options: UploadOptions
  ): Promise<string> {
    const response = await fetch(
      `${options.baseUrl}/api/files/${fileId}/download`,
      {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${options.token}`,
        },
      }
    );

    if (!response.ok) {
      throw new Error('Failed to get download URL');
    }

    const data = await response.json();
    return data.download_url || data.url;
  }

  /**
   * Delete a file
   */
  static async deleteFile(
    fileId: string,
    options: UploadOptions
  ): Promise<void> {
    const response = await fetch(
      `${options.baseUrl}/api/files/${fileId}`,
      {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${options.token}`,
        },
      }
    );

    if (!response.ok) {
      throw new Error('Failed to delete file');
    }
  }
}