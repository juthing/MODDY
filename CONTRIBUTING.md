# Contributing to Moddy

[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![Discord.py](https://img.shields.io/badge/discord.py-2.0+-blue.svg)](https://github.com/Rapptz/discord.py)
[![License](https://img.shields.io/badge/license-CC%20BY--NC--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)

Thank you for your interest in contributing to **Moddy**! This guide will help you understand how to **contribute effectively** to the project.
Whether you're fixing bugs, adding features, or improving documentation, your contributions are welcome.

## Getting Started

Before you start contributing, make sure you have:

- **Python 3.11+** installed on your system
- **Git** for version control
- A **PostgreSQL** database for local testing
- Basic knowledge of **discord.py** and **async Python**
- Familiarity with the **Discord API**

## Development Setup

### 1. Fork and Clone

Fork the repository and clone it locally:

```bash
git clone https://github.com/YOUR_USERNAME/MODDY.git
cd MODDY
```

### 2. Install Dependencies

Install the required Python packages:

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

> [!CAUTION]
> Never commit your `.env` file or expose your Discord token publicly!

Create a `.env` file with your configuration:

```env
DISCORD_TOKEN=your_bot_token_here
DATABASE_URL=your_postgresql_url_here
# Add other required environment variables
```

### 4. Run the Bot

Start the bot locally:

```bash
python main.py
```

## Contribution Guidelines

### Code Style

Following these guidelines will make your contributions easier to review and merge:

- Follow **PEP 8** Python style guidelines
- Use **type hints** for function parameters and return values
- Write **clear and descriptive** variable and function names
- Add **docstrings** to classes and functions
- Keep functions **focused and modular**

### Commit Messages

Write clear and descriptive commit messages:

- Use the **imperative mood** ("Add feature" not "Added feature")
- Start with a **verb** (Add, Fix, Update, Remove, Refactor)
- Keep the first line **under 50 characters**
- Add detailed description if needed after a blank line

Examples:
```
Add translation command for multiple languages
Fix reminder notification timing issue
Update PostgreSQL schema for user preferences
```

### Branch Naming

Use descriptive branch names:

- `feature/feature-name` for new features
- `fix/bug-description` for bug fixes
- `docs/documentation-update` for documentation changes
- `refactor/code-improvement` for refactoring

### Pull Requests

When submitting a pull request:

1. **Test your changes** thoroughly before submitting
2. **Update documentation** if you're adding or changing features
3. **Describe your changes** clearly in the PR description
4. **Reference related issues** using `#issue-number`
5. **Ensure all checks pass** before requesting review

## What to Contribute

### Bug Fixes

Found a bug? Great! Please:

- **Search existing issues** to avoid duplicates
- **Create an issue** describing the bug with reproduction steps
- **Submit a PR** with the fix and reference the issue

### New Features

Want to add a feature? Awesome!

- **Discuss the feature** in an issue first to get feedback
- **Keep it relevant** to Moddy's purpose (moderation and community management)
- **Maintain consistency** with existing features and code style
- **Add proper error handling** and user feedback

### Documentation

Documentation improvements are always welcome:

- Fix typos and grammatical errors
- Improve clarity and readability
- Add examples and usage guides
- Translate documentation (if applicable)

### Code Quality

Help improve code quality:

- Refactor complex or unclear code
- Improve performance and efficiency
- Add or improve type hints
- Enhance error handling

## Testing

> [!WARNING]
> Before submitting your contribution:
> - **Test all functionality** you've added or modified
> - **Test edge cases** and error scenarios
> - **Verify database operations** work correctly
> - **Check for memory leaks** in long-running operations
> - **Test with different Discord permissions** and scenarios

## Code Review Process

1. Submit your pull request
2. Maintainers will review your code
3. Address any requested changes
4. Once approved, your PR will be merged

**Note:** Reviews may take some time. Please be patient and responsive to feedback.

## Questions or Need Help?

If you have questions or need help:

- **Open an issue** for general questions
- **Join our Discord** (if available) for real-time discussions
- **Check existing documentation** and closed issues

## License

By contributing to Moddy, you agree that your contributions will be licensed under the **CC BY-NC-SA 4.0 International** license.

## Recognition

All contributors will be recognized in the project. Your contributions, big or small, help make Moddy better for everyone!

---

<div align="center">
  <strong>Thank you for contributing to Moddy!</strong> ❤️<br>
  Maintained by <a href="https://github.com/juthing">juthing</a>
</div>
