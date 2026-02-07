using System;
using System.Collections;
using System.Collections.Generic;
using System.Reflection;
using System.Linq;

namespace FFGui.Services;

public static class DynamicCloner
{
    public static T? DeepClone<T>(T? obj)
    {
        if (obj == null) return default;
        Type type = obj.GetType();

        // 1. Simple Types
        if (type.IsValueType || type == typeof(string)) return obj;

        // 2. Handle Arrays (Specifically fixes the string[] crash)
        if (type.IsArray)
        {
            var sourceArray = (Array)(object)obj;
            var elementType = type.GetElementType()!;
            var newArray = Array.CreateInstance(elementType, sourceArray.Length);
            for (int i = 0; i < sourceArray.Length; i++)
            {
                newArray.SetValue(DeepClone(sourceArray.GetValue(i)), i);
            }
            return (T?)(object)newArray;
        }

        // 3. Handle Dictionaries
        if (type.IsGenericType && type.GetGenericTypeDefinition() == typeof(Dictionary<,>))
        {
            IDictionary sourceDict = (IDictionary)obj;
            IDictionary? newDict = (IDictionary?)Activator.CreateInstance(type);
            if (newDict != null)
            {
                foreach (DictionaryEntry entry in sourceDict)
                {
                    newDict.Add(DeepClone(entry.Key)!, DeepClone(entry.Value));
                }
            }
            return (T?)newDict;
        }

        // 4. Handle Lists / Enumerable
        if (typeof(IEnumerable).IsAssignableFrom(type))
        {
            var underlyingType = type.GetGenericArguments().FirstOrDefault() ?? typeof(object);
            var genericListType = typeof(List<>).MakeGenericType(underlyingType);
            var newList = (IList?)Activator.CreateInstance(genericListType);

            if (newList != null)
            {
                foreach (var item in (IEnumerable)obj)
                {
                    newList.Add(DeepClone(item));
                }
            }
            return (T?)newList;
        }

        // 5. Handle Complex Objects (Classes/Records)
        object? clone = Activator.CreateInstance(type);
        if (clone == null) return default;

        foreach (var prop in type.GetProperties(BindingFlags.Public | BindingFlags.Instance))
        {
            if (prop.CanWrite && prop.GetIndexParameters().Length == 0)
                prop.SetValue(clone, DeepClone(prop.GetValue(obj)));
        }

        foreach (var field in type.GetFields(BindingFlags.Public | BindingFlags.Instance))
        {
            field.SetValue(clone, DeepClone(field.GetValue(obj)));
        }

        return (T)clone;
    }

    public static void UpdateProperties(object target, object source)
    {
        if (target == null || source == null) return;
        Type type = target.GetType();

        // Update Properties
        foreach (var prop in type.GetProperties(BindingFlags.Public | BindingFlags.Instance))
        {
            if (!prop.CanWrite || prop.GetIndexParameters().Length > 0) continue;

            object? sourceValue = prop.GetValue(source);

            // If it's a list, clear and refill
            if (typeof(IList).IsAssignableFrom(prop.PropertyType) && !prop.PropertyType.IsArray)
            {
                if (sourceValue is IList sourceList && prop.GetValue(target) is IList targetList)
                {
                    targetList.Clear();
                    foreach (var item in sourceList)
                        targetList.Add(DeepClone(item));
                }
            }
            else
            {
                // Otherwise, standard deep clone assignment
                prop.SetValue(target, DeepClone(sourceValue));
            }
        }

        // Update Fields
        foreach (var field in type.GetFields(BindingFlags.Public | BindingFlags.Instance))
        {
            object? sourceFieldValue = field.GetValue(source);

            if (typeof(IList).IsAssignableFrom(field.FieldType) && !field.FieldType.IsArray)
            {
                if (sourceFieldValue is IList sourceList && field.GetValue(target) is IList targetList)
                {
                    targetList.Clear();
                    foreach (var item in sourceList)
                        targetList.Add(DeepClone(item));
                }
            }
            else
            {
                field.SetValue(target, DeepClone(sourceFieldValue));
            }
        }
    }
}