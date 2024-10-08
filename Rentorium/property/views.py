from django.shortcuts import render, redirect, get_object_or_404
from .models import AllProperty, UserProfile
from .forms import *
from django.contrib import messages
from django.db.models import Q
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from urllib.parse import urlencode
from Agents.models import *
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

def add_property(request):
    if request.user.is_authenticated:        
        if request.method == 'POST':
            form = PropertyTypeForm(request.POST)
            if form.is_valid():
                selected_type = form.cleaned_data['Type']
                if selected_type in ['commercial', 'land', 'residential']:                    
                    return redirect('add_property_data', property_type=selected_type)
                
        else:
            form = PropertyTypeForm()

        return render(request, 'add_property.html', {'form':form})

    else:
        return redirect(reverse('signin') + '?next=' + request.path)
    

def add_property_data(request, property_type):
    if request.user.is_authenticated:
        if property_type == 'commercial':
            form_class = CommercialPropertyForm
        elif property_type == 'land':
            form_class = LandPropertyForm
        elif property_type == 'residential':
            form_class = ResidentialPropertyForm
        else:
            return redirect('add_property')

        if request.method == 'POST':
            user_profile = UserProfile.objects.get(user=request.user)
            form = form_class(request.POST, request.FILES)
            
            if form.is_valid():
                property_instance = form.save(commit=False)
                property_instance.user = user_profile
                property_instance.Property_type = property_type
                property_instance.save()

                messages.success(request, "Property added Successfully. Wait for the approval")
                return redirect('property_list')

            else:
                messages.error(request, "Something went wrong!")  
        else:
            form = form_class()
        return render(request, 'add_property_data.html', {'form': form, 'property_type':property_type})
    
    else:
        return redirect(reverse('signin') + '?next=' + request.path)

def update_property(request, property_id):
    if request.user.is_authenticated:
        property_instance = get_object_or_404(AllProperty, pk=property_id)
    
        if request.method == 'POST':
            property_instance.needs_approval = True 
            property_instance.save()
                
                # Determine the specific type of property and update its related fields
            if property_instance.Property_type == 'commercial':
                specific_form = CommercialPropertyForm(request.POST, instance=property_instance.commercialproperty)
            elif property_instance.Property_type == 'land':
                specific_form = LandPropertyForm(request.POST, instance=property_instance.landproperty)
            elif property_instance.Property_type == 'residential':
                specific_form = ResidentialPropertyForm(request.POST, instance=property_instance.residentialproperty)

            if specific_form.is_valid():                
                specific_form.save()
                
                return redirect('property_detail', pk=property_id)  # Redirect to property detail view after update
                
        else:
            #property_form = PropertyForm(instance=property_instance)
            if property_instance.Property_type == 'commercial':
                specific_form = CommercialPropertyForm(instance=property_instance.commercialproperty)
            elif property_instance.Property_type == 'land':
                specific_form = LandPropertyForm(instance=property_instance.landproperty)
            elif property_instance.Property_type == 'residential':
                specific_form = ResidentialPropertyForm(instance=property_instance.residentialproperty)
        
        return render(request, 'update_property.html', { 'specific_form': specific_form})
    else:
        return redirect(reverse('signin') + '?next=' + request.path)
    
    
def delete_property(request, property_id):
    if request.user.is_authenticated:
        property_instance = AllProperty.objects.get(pk=property_id)
        if request.method == 'POST':
            property_instance.delete()
            messages.success(request, "Property deleted successfully")
            return redirect('posted_properties')
        return render(request, 'property_detail.html', {'property_instance': property_instance})
    else:
        return redirect(reverse('signin') + '?next=' + request.path)
    

def property_detail(request, pk):
    property_instance = AllProperty.objects.get(pk = pk)
    
    if hasattr(property_instance, 'residentialproperty'):
        specific_property_instance = property_instance.residentialproperty
    elif hasattr(property_instance, 'commercialproperty'):
        specific_property_instance = property_instance.commercialproperty
    elif hasattr(property_instance, 'landproperty'):
        specific_property_instance = property_instance.landproperty
    else:
        # Handle the case where the property instance does not belong to any specific type
        specific_property_instance = None


    property_fields = {}
    
    if(specific_property_instance):
        property_fields = vars(specific_property_instance)
        property_fields['Property_Pictures'] = property_instance.Property_Pictures


    return render(request, "property_detail.html", {'property_fields':property_fields,'property.id':pk})


def filtering(request, properties):
    # Create an instance of the form
    filter_form = PropertyFilterForm(request.GET or None)
    # Check if form is submitted and valid
    if filter_form.is_valid():
        # Get cleaned data from the form
        cleaned_data = filter_form.cleaned_data
        property_type = cleaned_data.get('property_type')
        property_on = cleaned_data.get('property_on')
        area = cleaned_data.get('area')

        # Filter properties based on form data
        properties = properties.filter(Property_type=property_type) if property_type else properties
        properties = properties.filter(Property_on=property_on) if property_on else properties
        properties = properties.filter(Area=area) if area else properties

        # Additional filters based on property type
        if property_type == 'residential':
            bedrooms = cleaned_data.get('bedrooms')
            bathrooms = cleaned_data.get('bathrooms')

            properties = properties.filter(residentialproperty__Bedrooms=bedrooms) if bedrooms else properties
            properties = properties.filter(residentialproperty__Bathrooms=bathrooms) if bathrooms else properties

        elif property_type == 'commercial':
            business_type = cleaned_data.get('business_type')
            has_conference = cleaned_data.get('has_conference')
            has_security = cleaned_data.get('has_security')

            properties = properties.filter(commercialproperty__Business_type=business_type) if business_type else properties
            properties = properties.filter(commercialproperty__Has_conference_room=True) if has_conference else properties
            properties = properties.filter(commercialproperty__Has_security_system=True) if has_security else properties

        elif property_type == 'land':
            land_type = cleaned_data.get('land_type')

            properties = properties.filter(landproperty__Land_type=land_type) if land_type else properties


        ordering_choice = cleaned_data.get('ordering_choices')
        if ordering_choice == 'price_asc':
            properties = properties.order_by('Price')
        elif ordering_choice == 'price_desc':
            properties = properties.order_by('-Price')

    # Pagination
    paginator = Paginator(properties, 3)
    page_number = request.GET.get('page')
    try:
        properties = paginator.page(page_number)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page
        properties = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results
        properties = paginator.page(paginator.num_pages)

    return properties, filter_form



def property_list(request):
    properties = AllProperty.objects.filter(
        Q(Approval_by_Agent__isnull=False) & ~Q(Approval_by_Agent='Cancel') & ~Q(needs_approval=True)
    )


    properties, filter_form = filtering(request, properties)


    context = {
        'filtered_properties': properties,
        'filter_form': filter_form,
    }

    return render(request, 'property_list.html', context)




                
    context = {
        'filtered_properties': properties,
        'filter_form': filter_form,
    }
    return render(request, 'property_list.html', context)




def property_type(request):
    return render(request, "property_type.html")






def posted_properties(request):
    if request.user.is_authenticated:
        properties = AllProperty.objects.filter(user=request.user.UserProfile)
        properties, filter_form = filtering(request, properties)

        context = {
            'filtered_properties': properties,
            'filter_form': filter_form,
        }  
        return render(request, 'posted_properties.html', context)
    
    else:
        return redirect(reverse('signin') + '?next=' + request.path)
    

def view_property_documents(request, property_id):    
    if request.user.is_authenticated:
        property_instance = get_object_or_404(AllProperty, pk=property_id)
        if request.user.UserProfile.is_agent or property_instance.user_id:
            property_documents = property_instance.Property_Documents            
            return render(request, 'view_property_documents.html', {'property_instance': property_instance, 'property_documents': property_documents})
        else:
            messages.error(request, "You are not authorized to view the page")
            return redirect("/")
        
    else:
        return redirect(reverse('signin') + '?next=' + request.path)


