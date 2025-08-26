# SGR Part Manager

A Django-based inventory management system for Spring Garden Repair, designed to manage parts, engines, machines, and vendors with comprehensive filtering, sorting, and export capabilities.

## Features

### Core System
- **Django 5.0** with PostgreSQL/SQLite database support
- **Celery + Redis** for asynchronous task processing
- **HTMX** for dynamic frontend interactions
- **Responsive Design** with custom CSS using brand palette

### Inventory Management
- **Machines Management**: List, filter, sort, and export machine data
  - Filters: Make, Model, Year, Machine Type, Market Type
  - Server-side pagination (50 items per page)
  - CSV export with current filters
  - Detail pages showing machine information and related engines
- **Engines Management**: Comprehensive engine catalog with specifications
  - Filters: Engine Make/Model, SG Make/Model, Status
  - Global keyword search across all engine fields
  - Server-side pagination (50 items per page)
  - CSV export with current filters
  - Detail pages showing all engine specifications and related data
- **Parts Management**: Complete parts catalog with vendor relationships
  - Filters: Part Number, Name, Manufacturer, Category
  - Server-side pagination (50 items per page)
  - CSV export with current filters
  - Detail pages with tabbed interface for vendors and engine relationships
  - Stock aggregation across all vendors
- **Vendors Management**: Manage supplier information and relationships

### Data Models
- **SGEngine**: Spring Garden Engine catalog
- **Engine**: Detailed engine specifications with SG Engine relationships
- **Machine**: Equipment inventory with engine relationships
- **Part**: Parts catalog with vendor relationships
- **Vendor**: Supplier information
- **Through Models**: MachineEngine, EnginePart, PartVendor for relationships

### Admin Interface
- Full Django admin integration with custom list displays
- Advanced filtering and search capabilities
- Relationship management through through models

## Quick Start

### Prerequisites
- Python 3.8+
- PostgreSQL (optional, SQLite used for development)

### Installation

1. **Clone and setup**:
   ```bash
   git clone <repository-url>
   cd sgr_manager
   pip install -r requirements.txt
   ```

2. **Environment setup**:
   ```bash
   # Copy and edit environment variables
   cp .env.example .env
   # Edit .env with your database and Redis settings
   ```

3. **Database setup**:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

4. **Load demo data** (optional):
   ```bash
   python manage.py core_load_demo
   ```

5. **Run the application**:
   ```bash
   python manage.py runserver
   ```

6. **Start Celery worker** (optional):
   ```bash
   celery -A sgr_manager worker -l info
   ```

### URLs

- **Home**: `/` - Demo page with system overview
- **Admin**: `/admin/` - Django admin interface
- **Machines**: `/inventory/machines/` - Machine list with filters
- **Engines**: `/inventory/engines/` - Engine list with search and filters
- **Parts**: `/inventory/parts/` - Parts list with filters and vendor relationships
- **Inventory**: `/inventory/` - Inventory management overview

## Database Configuration

The system supports both SQLite (development) and PostgreSQL (production):

- **Development (SQLite)**: Set `USE_SQLITE=True` in environment (default)
- **Production (PostgreSQL)**: Set `USE_SQLITE=False` and configure PostgreSQL connection

## Demo Data

The `core_load_demo` management command creates sample data:
- 2 SGEngines (John Deere 4020, Ford 8N)
- 3 Engines with detailed specifications
- 2 Machines (John Deere 4020, Ford 8N)
- 2 Vendors (Tractor Supply Co., AgriParts Plus)
- 4 Parts with various categories
- Relationships between all entities

## Development

### Project Structure
```
sgr_manager/
├── core/                 # Core app with base templates and styles
├── inventory/           # Inventory management (machines, engines, parts)
├── imports/             # Import functionality (future)
├── sgr_manager/         # Project settings and configuration
└── templates/           # Global templates
```

### Key Files
- `core/templates/base.html` - Base template with navigation
- `core/static/core/styles.css` - Main CSS with brand palette
- `inventory/views.py` - Views for machines, engines, and parts
- `inventory/models.py` - All data models with relationships
- `inventory/admin.py` - Admin interface configuration

### Styling
The system uses a custom CSS design system with:
- Brand palette: Gray/red color scheme
- Responsive grid layouts
- Sticky table headers for better UX
- Consistent spacing and typography
- Tabbed interfaces for complex data display

## Contributing

1. Follow Django best practices
2. Use the existing CSS design system
3. Maintain responsive design principles
4. Test with the demo data before submitting changes

## License

[Add your license information here]
