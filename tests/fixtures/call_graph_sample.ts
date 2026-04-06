/**
 * Test sample with complex call graph for Phase 2 testing
 * Contains:
 * - Multi-level call relationships
 * - Method calls on objects
 * - Chained calls
 */


interface User {
  id: number;
  name: string;
  email: string;
}


export class UserService {
  private users: User[] = [];

  addUser(user: User): void {
    this.users.push(user);
  }

  findUserById(id: number): User | null {
    // @ts-ignore
    return this.users.find(u => u.id === id) || null;
  }

  validateUser(user: User): boolean {
    return this.validateEmail(user.email) && this.validateName(user.name);
  }

  private validateEmail(email: string): boolean {
    // @ts-ignore
    return email.includes('@');
  }

  private validateName(name: string): boolean {
    return name.length > 0;
  }
}


export class AuthService {
  private userService: UserService;

  constructor(userService: UserService) {
    this.userService = userService;
  }

  authenticate(userId: number, token: string): boolean {
    const user = this.userService.findUserById(userId);
    if (!user) {
      return false;
    }
    return this.validateToken(token);
  }

  private validateToken(token: string): boolean {
    return token.length > 10;
  }

  login(userId: number): string {
    const token = this.generateToken();
    if (this.authenticate(userId, token)) {
      return token;
    }
    throw new Error('Authentication failed');
  }

  private generateToken(): string {
    return 'token_' + Math.random().toString(36).substring(2);
  }
}
