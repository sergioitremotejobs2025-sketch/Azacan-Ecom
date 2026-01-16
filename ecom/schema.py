import graphene
import recommendations.schema
# Import graphql_types to ensure the converter is registered
import recommendations.graphql_types

class Query(recommendations.schema.Query, graphene.ObjectType):
    pass

class Mutation(recommendations.schema.Mutation, graphene.ObjectType):
    pass

schema = graphene.Schema(query=Query, mutation=Mutation)
