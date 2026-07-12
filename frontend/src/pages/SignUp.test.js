import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import SignUp from './SignUp';
import * as apiService from '../services/api';

jest.mock('../services/api');

const mockUsers = [
  { username: 'admin', email: 'admin@company.com', full_name: 'Administrator', is_active: true, last_login_at: '2026-07-06T05:49:36Z', login_frequency: 5 },
  { username: 'manager1', email: 'm1@company.com', full_name: 'Manager One', is_active: true, last_login_at: null, login_frequency: 0 }
];

describe('SignUp Admin Panel', () => {
  beforeEach(() => {
    apiService.listUsers.mockResolvedValue(mockUsers);
    apiService.deleteUser.mockResolvedValue({ status: 'success' });
    jest.spyOn(window, 'confirm').mockImplementation(() => true);
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('renders registered manager accounts and shows actions column', async () => {
    render(<SignUp isAdminPanel={true} onNotify={jest.fn()} />);

    expect(await screen.findByText('manager1')).toBeInTheDocument();
    expect(screen.getByText('Actions')).toBeInTheDocument();
    expect(screen.getByText('System')).toBeInTheDocument();

    const deleteButtons = screen.getAllByRole('button', { name: /delete/i });
    expect(deleteButtons.length).toBe(1);
  });

  it('triggers delete confirmation and deletes user on clicking delete', async () => {
    const notifyMock = jest.fn();
    render(<SignUp isAdminPanel={true} onNotify={notifyMock} />);

    expect(await screen.findByText('manager1')).toBeInTheDocument();

    const deleteBtn = screen.getByRole('button', { name: /delete/i });
    fireEvent.click(deleteBtn);

    expect(window.confirm).toHaveBeenCalledWith(
      'Are you sure you want to permanently delete the account for "manager1"?'
    );

    await waitFor(() => {
      expect(apiService.deleteUser).toHaveBeenCalledWith('manager1');
      expect(notifyMock).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'success',
          title: 'Account deleted'
        })
      );
    });
  });
});
