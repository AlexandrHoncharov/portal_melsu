# Миграция с «case‑вкладок» на React Router v6

Инструкция показывает, как заменить текущую логику переключения вкладок  
(`switch/case` + re‑render) на полноценную маршрутизацию через **React Router v6**.

> **Почему это лучше**  
> • Читаемый URL ↔ состояние страницы  
> • Работают кнопки «Назад/Вперёд» и F5  
> • Легко делиться ссылками  
> • Lazy‑loading страниц и чище код

---

## 1  Установка

```bash
# yarn
yarn add react-router-dom@6

# npm
npm i react-router-dom@6
```

---

## 2  Новая структура

```
src/
 ├─ pages/                 # каждая вкладка — отдельный файл
 │   ├─ Auth.jsx
 │   ├─ Profile.jsx
 │   ├─ Applications.jsx
 │   ├─ Schedule.jsx
 │   ├─ ConstructorReports.jsx
 │   ├─ ConstructorApplications.jsx
 │   ├─ Structure.jsx
 │   └─ NotFound.jsx
 ├─ layout/
 │   ├─ DashboardLayout.jsx  # Sidebar + <Outlet/>
 │   └─ ProtectedRoute.jsx   # гард по токену/ролям
 ├─ components/ …           # остаётся как было
 └─ main.jsx
```

---

## 3  `main.jsx` — маршруты

```jsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Auth               from './pages/Auth.jsx';
import DashboardLayout    from './layout/DashboardLayout.jsx';
import ProtectedRoute     from './layout/ProtectedRoute.jsx';
import Profile            from './pages/Profile.jsx';
import Applications       from './pages/Applications.jsx';
import Report             from './pages/Report.jsx';
import Schedule           from './pages/Schedule.jsx';
import ConstructorReports from './pages/ConstructorReports.jsx';
import ConstructorApps    from './pages/ConstructorApplications.jsx';
import Structure          from './pages/Structure.jsx';
import NotFound           from './pages/NotFound.jsx';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* публичная страница */}
        <Route path="/auth" element={<Auth />} />

        {/* защищённая зона */}
        <Route element={<ProtectedRoute />}>
          <Route element={<DashboardLayout />}>
            <Route index element={<Navigate to="profile" replace />} />
            <Route path="profile"                element={<Profile />} />
            <Route path="applications"           element={<Applications />} />
            <Route path="reports"                element={<Report />} />
            <Route path="schedule"               element={<Schedule />} />
            <Route path="constructor/reports"    element={<ConstructorReports />} />
            <Route path="constructor/applications" element={<ConstructorApps />} />
            <Route path="structure"              element={<Structure />} />
          </Route>
        </Route>

        {/* 404 */}
        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  );
}
```

---

## 4  `ProtectedRoute.jsx`

```jsx
import { Navigate, Outlet } from 'react-router-dom';
import api from '../api/api.js';  // ваш ApiClient

export default function ProtectedRoute() {
  return api.isAuthenticated()
    ? <Outlet />            // рендер вложенных маршрутов
    : <Navigate to="/auth" replace />;
}
```

---

## 5  `DashboardLayout.jsx` — Sidebar + `<Outlet />`

```jsx
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import Sidebar from '../components/SideBar';
import api     from '../api/api.js';
import { useEffect, useState } from 'react';

export default function DashboardLayout() {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);

  useEffect(() => { api.getUserProfile().then(setUser); }, []);

  if (!user) return <div>Loading…</div>;

  const roles = user.roles;

  return (
    <>
      <Sidebar username={user.username}>
        <NavLink to="profile">Профиль</NavLink>
        {roles.includes('Сотрудник') && <NavLink to="applications">Заявки</NavLink>}
        {roles.includes('Админ')     && <NavLink to="structure">Структура</NavLink>}
        <button onClick={() => { api.logout(); navigate('/auth'); }}>
          Выйти
        </button>
      </Sidebar>

      <main className="p-4">
        <Outlet />   {/* активная страница */}
      </main>
    </>
  );
}
```

---

## 6  Удаляем старый `switch/case`

* Удаляем state `activeIndex` и `switch`.
* В Sidebar используем `<NavLink>` вместо `onClick`.
* `useEffect`, зависящие от `activeIndex`, больше не нужны — каждая страница сама загружает данные.

---

## 7  Ленивая подгрузка (опция)

```jsx
import { lazy, Suspense } from 'react';

const Profile = lazy(() => import('./pages/Profile.jsx'));

<Suspense fallback={<div>Загрузка…</div>}>
  <Routes> … </Routes>
</Suspense>
```

---

## 8  Финальная проверка

1. Запустите `npm run dev` / `yarn dev`.  
2. Откройте `/profile`, `/applications` и другие URL — контент меняется без перезагрузки.  
3. Обновление страницы сохраняет состояние.  
4. Кнопки «Назад / Вперёд» работают.  
5. В коде больше нет `activeIndex`.

---

Готово! Вкладки теперь живут в URL‑ах, приложение дружелюбно к пользователю, а код чище.
