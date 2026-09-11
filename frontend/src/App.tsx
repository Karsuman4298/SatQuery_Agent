import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { HistoryProvider } from './context/HistoryContext';
import { ReportsProvider } from './context/ReportsContext';
import ProtectedRoute from './components/common/ProtectedRoute';
import EntryPage from './pages/EntryPage/EntryPage';
import SignInPage from './pages/Auth/SignInPage';
import SignUpPage from './pages/Auth/SignUpPage';
import DashboardPage from './pages/Dashboard/DashboardPage';
import NewAnalysisPage from './pages/NewAnalysis/NewAnalysisPage';
import WorkspacePage from './pages/Workspace/WorkspacePage';
import HistoryPage from './pages/History/HistoryPage';
import ReportsPage from './pages/Reports/ReportsPage';
import ProfilePage from './pages/Profile/ProfilePage';
import './index.css';

function App() {
  return (
    <AuthProvider>
      <HistoryProvider>
        <ReportsProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/" element={<EntryPage />} />
              <Route path="/login" element={<SignInPage />} />
              <Route path="/auth/signin" element={<SignInPage />} />
              <Route path="/signup" element={<SignUpPage />} />
              <Route path="/auth/signup" element={<SignUpPage />} />

              <Route
                path="/dashboard"
                element={
                  <ProtectedRoute>
                    <DashboardPage />
                  </ProtectedRoute>
                }
              />

              {/* History page */}
              <Route
                path="/history"
                element={
                  <ProtectedRoute>
                    <HistoryPage />
                  </ProtectedRoute>
                }
              />

              {/* Reports page */}
              <Route
                path="/reports"
                element={
                  <ProtectedRoute>
                    <ReportsPage />
                  </ProtectedRoute>
                }
              />

              {/* Profile page */}
              <Route
                path="/profile"
                element={
                  <ProtectedRoute>
                    <ProfilePage />
                  </ProtectedRoute>
                }
              />

              {/* New Analysis upload/selection screen */}
              <Route
                path="/new-analysis"
                element={
                  <ProtectedRoute>
                    <NewAnalysisPage />
                  </ProtectedRoute>
                }
              />

              {/* Analysis Workspace — opens existing or new analysis */}
              <Route
                path="/analysis/:id"
                element={
                  <ProtectedRoute>
                    <WorkspacePage />
                  </ProtectedRoute>
                }
              />

              {/* Legacy /workspace redirect to new-analysis */}
              <Route path="/workspace" element={<Navigate to="/new-analysis" replace />} />

              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </BrowserRouter>
        </ReportsProvider>
      </HistoryProvider>
    </AuthProvider>
  );
}

export default App;
