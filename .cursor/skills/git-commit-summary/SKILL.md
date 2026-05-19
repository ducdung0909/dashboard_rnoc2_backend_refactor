---
name: git-commit-summary
description: Tạo commit message ngắn gọn cho git sau khi tạo code mới. Dùng khi user muốn commit, tạo git message, hoặc hỏi về commit message.
---

# Git Commit Summary

## Mục Đích

Tạo commit message ngắn gọn, có ý nghĩa cho git sau mỗi lần tạo code mới.

## Quy Tắc Commit Message

### Cấu Trúc

```
<type>(<scope>): <mô tả ngắn>

[<mô tả chi tiết (tùy chọn)>]
```

### Type Conventions

| Type | Dùng cho |
|------|----------|
| `feat` | Tính năng mới |
| `fix` | Sửa bug |
| `refactor` | Cấu trúc lại code |
| `docs` | Tài liệu |
| `test` | Test case |
| `chore` | Công việc phụ (config, build) |
| `perf` | Cải thiện hiệu suất |

### Ví Dụ

**Thêm API endpoint mới:**
```
feat(api): thêm endpoint /users cho user management

- GET /users - lấy danh sách users
- POST /users - tạo user mới
```

**Sửa bug:**
```
fix(auth): fix lỗi token hết hạn không redirect về login

Trước đây user bị stuck ở trang dashboard khi token expired
```

**Refactor:**
```
refactor(db): chuyển từ raw query sang ORM

Sử dụng SQLAlchemy để thống nhất data access layer
```

## Workflow

1. **Analyze**: Xem xét code thay đổi gì
2. **Identify**: Xác định type phù hợp
3. **Write**: Viết message theo cấu trúc
4. **Suggest**: Đề xuất cho user

## Lưu Ý

- Mô tả ngắn: tối đa 50-72 ký tự
- Dùng tiếng Việt cho mô tả
- Focus vào **"what"** và **"why"**, không phải **"how"**
- Không viết hoa đầu dòng
- Không dùng dấu chấm cuối dòng mô tả ngắn
