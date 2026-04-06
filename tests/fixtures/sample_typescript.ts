/**
 * 示例 TypeScript 文件用于测试
 */

interface User {
    id: number;
    username: string;
    email: string;
}

class ApiClient {
    post<T>(s: string, param2: { username: string; password: string }) {
        // @ts-ignore
        return Promise.resolve(undefined);
    }
}

export class AuthService {
    private token: string | null = null;

    constructor(private apiClient: ApiClient) {
    }

    // @ts-ignore
    async login(username: string, password: string): Promise<string> {
        const user = await this.validateCredentials(username, password);
        if (user) {
            this.token = this.generateToken(user.id);
            return this.token;
        }
        throw new Error('Invalid credentials');
    }

    private validateCredentials(username: string, password: string): Promise<User | null> {
        return this.apiClient.post<User>('/auth/login', { username, password });
    }

    private generateToken(userId: number): string {
        return `token_${userId}_${Date.now()}`;
    }

    logout(): void {
        this.token = null;
    }
}

export function formatDate(date: Date): string {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1);
    const day = String(date.getDate());
    return `${year}-${month}-${day}`;
}

export const API_BASE_URL = 'https://api.example.com';
