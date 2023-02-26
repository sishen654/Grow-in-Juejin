import { ActionType } from "@/types";

export const fetchUserProfile = async (userId?: string | null) => {
    try {
        const res = await fetch("https://api.juejin.cn/user_api/v1/user/get" + (userId ? `?user_id=${userId}` : "")).then(res => res.json())
        return res.data;
    } catch (error) {
        throw new Error("Request Failed")
    }
}

export const fetchUserDynamic = async (userId: string, cursor: string): Promise<{
    cursor: string, list: Array<{
        time: number,
        id: number,
        action: ActionType
    }>,
    hasMore: boolean,
    count: number
}> => {
    try {
        const res = await fetch(`https://api.juejin.cn/user_api/v1/user/dynamic?user_id=${userId}&cursor=${cursor}`).then(res => res.json())
        return res.data;
    } catch (error) {
        throw new Error("Request Failed")
    }
}

export const fetchUserArticles = async (userId: string, cursor: number) => {
    try {
        const res = await fetch(`https://api.juejin.cn/content_api/v1/article/query_list`, {
            method: "POST",
            body: JSON.stringify({
                user_id: userId,
                cursor,
                sort_type: 2
            })
        }).then(res => res.json())
        return res.data;
    } catch (error) {
        throw new Error("Request Failed")
    }
}

export const fetchUserPins = async (userId: string, cursor: number) => {
    try {
        const res = await fetch(`https://api.juejin.cn/content_api/v1/short_msg/query_list`, {
            method: "POST",
            body: JSON.stringify({
                user_id: userId,
                cursor,
                limit: 20,
                sort_type: 4
            })
        }).then(res => res.json())
        return res.data;
    } catch (error) {
        throw new Error("Request Failed")
    }
}

export const fetchActivities = async () => {
    try {
        const res = await fetch("https://raw.githubusercontent.com/curly210102/grow-in-juejin/main/activity.json").then(res => res.json())
        return res;
    } catch (error) {
        throw new Error("Request Failed")
    }
}