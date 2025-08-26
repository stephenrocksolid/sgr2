# HTMX Add/Remove Row Fix Template

## Quick Reference for Screenshot Analysis

When you send a screenshot of a page with HTMX add/remove issues, I'll extract the following information and apply the appropriate fixes:

### 1. Page Identification
- **URL Pattern**: Extract from browser address bar
- **Page Type**: Detail page, list page, etc.
- **Section Name**: The problematic section (e.g., "Related Engines", "Related Parts", "Vendors")

### 2. Issue Classification
- **Add Issues**: Form stays visible, doesn't work, HTMX errors
- **Remove Issues**: 404 errors, doesn't work, HTMX errors
- **Display Issues**: Table doesn't render initially, unstable containers

### 3. Standard Fix Patterns

#### Pattern A: Stable Container + Collapsible Form
**Use for**: Sections that need to show/hide forms and maintain state

```html
<!-- Main page template -->
<div id="[section]-container"
     hx-get="{% url '[app]:[section]_partial' [object].id %}"
     hx-trigger="load"
     hx-target="this"
     hx-swap="innerHTML">
  <div class="loading-placeholder">Loading...</div>
</div>
```

```html
<!-- Partial template -->
{% if items %}
    <table class="related-table">
        <!-- Table content -->
    </table>
{% else %}
    <div class="empty-message">No items yet.</div>
{% endif %}

<div class="mt-3" id="add-item-region">
    {% if show_form or form.errors %}
        <!-- Expanded form -->
        <form hx-post="{% url '[app]:[section]_add' [object].id %}"
              hx-target="#[section]-container"
              hx-swap="innerHTML">
            {% csrf_token %}
            {{ form.as_p }}
            <button type="submit">Add</button>
            <button type="button" hx-get="{% url '[app]:[section]_partial' [object].id %}"
                    hx-target="#[section]-container">Cancel</button>
        </form>
    {% else %}
        <!-- Collapsed button -->
        <button hx-get="{% url '[app]:[section]_partial' [object].id %}?show_form=1"
                hx-target="#[section]-container">Add Item</button>
    {% endif %}
</div>
```

#### Pattern B: Simple Add/Remove
**Use for**: Basic add/remove without form state management

```html
<!-- Add form -->
<form hx-post="{% url '[app]:[section]_add' [object].id %}"
      hx-target="#[section]-container"
      hx-swap="innerHTML">
    {% csrf_token %}
    <!-- Form fields -->
</form>

<!-- Remove button -->
<form hx-post="{% url '[app]:[section]_remove' [object].id item.id %}"
      hx-target="#[section]-container"
      hx-swap="innerHTML"
      hx-confirm="Are you sure?">
    {% csrf_token %}
    <button type="submit">Remove</button>
</form>
```

### 4. URL Pattern Standards

#### Standard URL Structure
```
# Partial rendering
[model]/<int:[model]_id>/[relation]/partial/

# Add operation
[model]/<int:[model]_id>/[relation]/add/

# Remove operation  
[model]/<int:[model]_id>/[relation]/<int:link_id>/remove/
```

#### Examples
```
# Engines
machines/<int:machine_id>/engines/partial/
machines/<int:machine_id>/engines/add/
machines/<int:machine_id>/engines/<int:link_id>/remove/

# Parts
machines/<int:machine_id>/parts/partial/
machines/<int:machine_id>/parts/add/
machines/<int:machine_id>/parts/<int:link_id>/remove/

# Vendors
parts/<int:part_id>/vendors/partial/
parts/<int:part_id>/vendors/add/
parts/<int:part_id>/vendors/<int:link_id>/remove/
```

### 5. View Function Templates

#### Partial View
```python
@login_required
def [model]_[relation]_partial(request, [model]_id):
    [model] = get_object_or_404([Model], pk=[model]_id)
    items = [model].[relation]_set.select_related('[related_field]').all()
    show_form = request.GET.get('show_form') == '1'
    form = [Model][Relation]Form([model]=[model])
    
    return render(request, '[app]/partials/_[model]_[relation]_partial.html', {
        '[model]': [model],
        'items': items,
        'form': form,
        'show_form': show_form,
    })
```

#### Add View
```python
@login_required
@require_http_methods(["POST"])
def [model]_[relation]_add(request, [model]_id):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    
    [model] = get_object_or_404([Model], pk=[model]_id)
    form = [Model][Relation]Form(request.POST, [model]=[model])
    
    if form.is_valid():
        form.save()
        items = [model].[relation]_set.select_related('[related_field]').all()
        return render(request, '[app]/partials/_[model]_[relation]_partial.html', {
            '[model]': [model],
            'items': items,
            'form': [Model][Relation]Form([model]=[model]),
            'show_form': False,
        })
    
    # Error case
    items = [model].[relation]_set.select_related('[related_field]').all()
    response = render(request, '[app]/partials/_[model]_[relation]_partial.html', {
        '[model]': [model],
        'items': items,
        'form': form,
        'show_form': True,
    })
    response.status_code = 400
    return response
```

#### Remove View
```python
@login_required
@require_http_methods(["POST"])
def [model]_[relation]_remove(request, [model]_id, link_id):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    
    [model] = get_object_or_404([Model], pk=[model]_id)
    link = get_object_or_404([RelationModel], pk=link_id, [model]=[model])
    link.delete()
    
    items = [model].[relation]_set.select_related('[related_field]').all()
    return render(request, '[app]/partials/_[model]_[relation]_partial.html', {
        '[model]': [model],
        'items': items,
        'form': [Model][Relation]Form([model]=[model]),
        'show_form': False,
    })
```

### 6. Form Class Template

```python
class [Model][Relation]Form(forms.ModelForm):
    class Meta:
        model = [RelationModel]
        fields = ['[field1]', '[field2]', 'notes']
    
    def __init__(self, *args, [model]=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.[model] = [model]
        
        if [model]:
            # Filter available choices
            existing_ids = [model].[relation]_set.values_list('[field1]_id', flat=True)
            available_items = [RelatedModel].objects.exclude(id__in=existing_ids)
            self.fields['[field1]'].choices = [('', 'Choose...')] + [(item.id, str(item)) for item in available_items]
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.[model]:
            instance.[model] = self.[model]
        if commit:
            instance.save()
        return instance
```

### 7. Common Issues & Solutions

#### Issue: 404 on Remove
**Cause**: Conflicting URL patterns or wrong parameter names
**Solution**: Remove legacy URL patterns, ensure consistent parameter naming

#### Issue: Form Stays Visible After Add
**Cause**: Not returning collapsed state
**Solution**: Return partial with `show_form=False`

#### Issue: HTMX Target Errors
**Cause**: Unstable containers or missing elements
**Solution**: Use stable container that always exists

#### Issue: CSRF Errors
**Cause**: Missing CSRF token in forms
**Solution**: Add `{% csrf_token %}` to all forms

#### Issue: Duplicate IDs
**Cause**: Using IDs in loops
**Solution**: Use `data-*` attributes instead

#### Issue: "No available items" when items exist
**Cause**: Form logic incorrectly filtering available choices
**Solution**: Fix form field filtering and choice logic

**Detailed Fix**:
```python
# In the form class __init__ method
def __init__(self, *args, [model]=None, **kwargs):
    super().__init__(*args, **kwargs)
    self.[model] = [model]
    
    if [model]:
        # Get items that are NOT already associated with this [model]
        existing_ids = [model].[relation]_set.values_list('[field]_id', flat=True)
        available_items = [RelatedModel].objects.exclude(id__in=existing_ids).order_by('[sort_field]')
        
        # Set up choices with proper filtering
        choices = [('', 'Choose an item...')]
        for item in available_items:
            display_name = f"{item.field1} {item.field2}"
            if hasattr(item, 'related_field') and item.related_field:
                display_name += f" ({item.related_field})"
            choices.append((item.id, display_name))
        
        self.fields['[field]'].choices = choices
```

**Template Logic**:
```html
{% if form.fields.[field].choices|length > 1 %}
    <button class="btn btn-secondary"
            hx-get="{% url '[app]:[section]_partial' [object].pk %}?show_form=1"
            hx-target="#[section]-container"
            hx-swap="innerHTML">
        Add [Item]
    </button>
{% else %}
    <div class="alert alert-info">
        No available [items] to add. All [items] are already associated with this [object].
    </div>
{% endif %}
```

**Common Causes**:
- Form not filtering correctly (check the `exclude()` query)
- Wrong field name in `values_list()`
- Missing `order_by()` causing inconsistent results
- Form not being passed the correct [model] instance

### 8. File Structure Standards

```
[app]/
├── urls.py                    # URL patterns
├── views.py                   # View functions
├── forms.py                   # Form classes
└── templates/
    └── [app]/
        ├── [page].html        # Main page template
        └── partials/
            └── _[section]_partial.html  # Partial template
```

### 9. Testing Checklist

- [ ] Page loads with stable container
- [ ] Add button expands form
- [ ] Form submission works
- [ ] Form collapses after successful add
- [ ] Remove button works
- [ ] No 404 errors in console
- [ ] No HTMX target errors
- [ ] CSRF protection working
- [ ] Confirmation dialogs work
- [ ] Empty states display correctly

### 10. Quick Fix Commands

```bash
# Check for syntax errors
python manage.py check

# Test URL generation
python manage.py shell -c "from django.urls import reverse; print(reverse('[app]:[view]', kwargs={...}))"

# Check for conflicting URLs
grep -r "path.*remove" [app]/urls.py
```

---

## Usage Instructions

When you send a screenshot:

1. **I'll extract**: Page URL, section name, and issue type
2. **I'll identify**: The appropriate pattern to use
3. **I'll apply**: The fixes using the templates above
4. **I'll test**: The implementation for common issues
5. **I'll document**: The changes made

This template covers 90% of HTMX add/remove issues you'll encounter. For edge cases, I'll adapt these patterns as needed.

---

## Special Case: "No Available Items" Issue

### Problem Description
When you see "No available [items] to add" but you know there are items in the database that could be added, this is typically a form filtering issue.

### Root Cause
The form's `__init__` method is incorrectly filtering the available choices, usually due to:
1. Wrong field name in the `values_list()` query
2. Incorrect relationship field name
3. Form not receiving the correct model instance
4. Missing or incorrect `exclude()` logic

### Quick Fix Template

#### 1. Check the Form Class
```python
class [Model][Relation]Form(forms.ModelForm):
    def __init__(self, *args, [model]=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.[model] = [model]
        
        if [model]:
            # DEBUG: Check what's happening
            print(f"DEBUG: [model] ID: {[model].id}")
            print(f"DEBUG: Existing [relation] count: {[model].[relation]_set.count()}")
            
            # Get existing items
            existing_ids = [model].[relation]_set.values_list('[field]_id', flat=True)
            print(f"DEBUG: Existing IDs: {list(existing_ids)}")
            
            # Get available items
            available_items = [RelatedModel].objects.exclude(id__in=existing_ids)
            print(f"DEBUG: Available items count: {available_items.count()}")
            
            # Set up choices
            choices = [('', 'Choose an item...')]
            for item in available_items:
                display_name = f"{item.field1} {item.field2}"
                choices.append((item.id, display_name))
            
            self.fields['[field]'].choices = choices
```

#### 2. Common Field Name Patterns
```python
# For MachineEngine (machine -> engine)
existing_ids = machine.machineengine_set.values_list('engine_id', flat=True)
available_items = Engine.objects.exclude(id__in=existing_ids)

# For MachinePart (machine -> part)  
existing_ids = machine.machinepart_set.values_list('part_id', flat=True)
available_items = Part.objects.exclude(id__in=existing_ids)

# For PartVendor (part -> vendor)
existing_ids = part.partvendor_set.values_list('vendor_id', flat=True)
available_items = Vendor.objects.exclude(id__in=existing_ids)

# For EnginePart (engine -> part)
existing_ids = engine.enginepart_set.values_list('part_id', flat=True)
available_items = Part.objects.exclude(id__in=existing_ids)
```

#### 3. Template Debug Version
```html
<!-- Add this temporarily to debug -->
<div class="debug-info" style="background: #f0f0f0; padding: 10px; margin: 10px 0; font-size: 12px;">
    <strong>DEBUG:</strong><br>
    Form field choices count: {{ form.fields.[field].choices|length }}<br>
    Available choices: {{ form.fields.[field].choices|slice:":5" }}<br>
    [Model] ID: {{ [model].id }}<br>
    Existing [relation] count: {{ [model].[relation]_set.count }}
</div>

{% if form.fields.[field].choices|length > 1 %}
    <button class="btn btn-secondary">Add [Item]</button>
{% else %}
    <div class="alert alert-info">
        No available [items] to add. (DEBUG: {{ form.fields.[field].choices|length }} choices)
    </div>
{% endif %}
```

### Quick Diagnostic Steps

1. **Check the relationship field name**:
   ```python
   # In Django shell
   from [app].models import [Model]
   [model] = [Model].objects.first()
   print([model].[relation]_set.all())  # Should show existing relationships
   ```

2. **Verify the form is getting the model**:
   ```python
   # In the view, add debug print
   print(f"DEBUG: Form [model] = {[model]}")
   form = [Model][Relation]Form([model]=[model])
   print(f"DEBUG: Form choices count = {len(form.fields['[field]'].choices)}")
   ```

3. **Check the exclude query**:
   ```python
   # Test the query directly
   existing_ids = [model].[relation]_set.values_list('[field]_id', flat=True)
   print(f"DEBUG: Existing IDs: {list(existing_ids)}")
   
   available = [RelatedModel].objects.exclude(id__in=existing_ids)
   print(f"DEBUG: Available count: {available.count()}")
   ```

### Example: Engine Fix Applied
```python
# Before (broken)
existing_engine_ids = machine.machineengine_set.values_list('engine_id', flat=True)
available_engines = Engine.objects.exclude(id__in=existing_engine_ids)

# After (working)
existing_engine_ids = machine.machineengine_set.values_list('engine_id', flat=True)
available_engines = Engine.objects.exclude(id__in=existing_engine_ids).order_by('engine_make', 'engine_model')

# Template check
{% if form.fields.engine.choices|length > 1 %}
    <button>Add Engine</button>
{% else %}
    <div class="alert">No available engines...</div>
{% endif %}
```

### When to Use This Fix
- You see "No available [items]" but know items exist in the database
- The Add button doesn't appear when it should
- Form dropdown is empty when it should have choices
- HTMX add functionality seems to work but shows wrong message
